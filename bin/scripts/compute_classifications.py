#!/usr/bin/env python
"""
Classify many DescriptorElements from a DescriptorIndex based on an input
set of element UUIDs, producing ClassificationElements for each via the
configured factory, outputting a CSV file of classification results.
"""
import csv
import logging
import os

from smqtk.algorithms import (
    get_classifier_impls
)
from smqtk.representation import (
    ClassificationElementFactory,
    get_classification_element_impls,
    get_descriptor_index_impls,
)
from smqtk.utils import (
    bin_utils,
    file_utils,
    parallel,
    plugin,
)


__author__ = "paul.tunison@kitware.com"


def default_config():
    return {
        "utility": {
            "uuids_list_filepath": "CHANGE ME :: PATH",
            "output_csv_header_filepath": "CHANGE ME :: PATH",
            "output_csv_filepath": "CHANGE ME :: PATH",
            "classify_overwrite": False,
            "parallel": {
                "use_multiprocessing": False,
                "index_extraction_cores": None,
                "classification_cores": None,
            }
        },
        "plugins": {
            "classifier": plugin.make_config(get_classifier_impls()),
            "classification_factory": plugin.make_config(
                get_classification_element_impls()
            ),
            "descriptor_index": plugin.make_config(
                get_descriptor_index_impls()
            ),
        }
    }


def main():
    description = """
    Script for asynchronously computing classifications for DescriptorElements
    in a DescriptorIndex specified via a list of UUIDs. Results are output to a
    CSV file in the format:

        uuid, label1_confidence, label2_confidence, ...

    CSV columns labels are output to the given CSV header file path. Label
    columns will be in the order as reported by the classifier implementations
    ``get_labels`` method.

    Due to using an input file-list of UUIDs, we require that the UUIDs of
    indexed descriptors be strings, or equality comparable to the UUIDs' string
    representation.
    """

    args, config = bin_utils.utility_main_helper(
        default_config(),
        description,
    )
    log = logging.getLogger()

    # - parallel_map UUIDs to load from the configured index
    # - classify iterated descriptors

    uuids_list_filepath = config['utility']['uuids_list_filepath']
    output_csv_filepath = config['utility']['output_csv_filepath']
    output_csv_header_filepath = \
        config['utility']['output_csv_header_filepath']
    classify_overwrite = config['utility']['classify_overwrite']

    p_use_multiprocessing = \
        config['utility']['parallel']['use_multiprocessing']
    p_index_extraction_cores = \
        config['utility']['parallel']['index_extraction_cores']
    p_classification_cores = \
        config['utility']['parallel']['classification_cores']

    if not uuids_list_filepath:
        raise ValueError("No uuids_list_filepath specified.")
    elif not os.path.isfile(uuids_list_filepath):
        raise ValueError("Given uuids_list_filepath did not point to a file.")

    #
    # Initialize configured plugins
    #

    log.info("Initializing descriptor index")
    #: :type: smqtk.representation.DescriptorIndex
    descriptor_index = plugin.from_plugin_config(
        config['plugins']['descriptor_index'],
        get_descriptor_index_impls()
    )

    log.info("Initializing classification factory")
    c_factory = ClassificationElementFactory.from_config(
        config['plugins']['classification_factory']
    )

    log.info("Initializing classifier")
    #: :type: smqtk.algorithms.Classifier
    classifier = plugin.from_plugin_config(
        config['plugins']['classifier'], get_classifier_impls()
    )

    #
    # Setup/Process
    #
    def iter_uuids():
        with open(uuids_list_filepath) as f:
            for l in f:
                yield l.strip()

    def descr_for_uuid(uuid):
        """
        :type uuid: collections.Hashable
        :rtype: smqtk.representation.DescriptorElement
        """
        return descriptor_index.get_descriptor(uuid)

    def classify_descr(d):
        """
        :type d: smqtk.representation.DescriptorElement
        :rtype: smqtk.representation.ClassificationElement
        """
        return classifier.classify(d, c_factory, classify_overwrite)

    log.info("Initializing uuid-to-descriptor parallel map")
    #: :type: collections.Iterable[smqtk.representation.DescriptorElement]
    element_iter = parallel.parallel_map(
        descr_for_uuid, iter_uuids(),
        use_multiprocessing=p_use_multiprocessing,
        cores=p_index_extraction_cores,
        name="descr_for_uuid",
    )

    log.info("Initializing descriptor-to-classification parallel map")
    #: :type: collections.Iterable[smqtk.representation.ClassificationElement]
    classification_iter = parallel.parallel_map(
        classify_descr, element_iter,
        use_multiprocessing=p_use_multiprocessing,
        cores=p_classification_cores,
        name='classify_descr',
    )

    c_labels = classifier.get_labels()

    def make_row(c):
        """
        :type c: smqtk.representation.ClassificationElement
        """
        c_m = c.get_classification()
        return [c.uuid] + [c_m[l] for l in c_labels]

    #
    # Write/Output files
    #

    # column labels file
    log.info("Writing CSV column header file: %s", output_csv_header_filepath)
    file_utils.safe_create_dir(os.path.dirname(output_csv_header_filepath))
    with open(output_csv_header_filepath, 'wb') as f_csv:
        w = csv.writer(f_csv)
        w.writerow(['uuid'] + c_labels)

    # CSV file
    log.info("Writing CSV data file: %s", output_csv_filepath)
    file_utils.safe_create_dir(os.path.dirname(output_csv_filepath))
    r_state = [0] * 7
    with open(output_csv_filepath, 'wb') as f_csv:
        w = csv.writer(f_csv)
        for c in classification_iter:
            w.writerow(make_row(c))
            bin_utils.report_progress(log.info, r_state, 1.0)

    # Final report
    r_state[1] -= 1
    bin_utils.report_progress(log.info, r_state, 0)

    log.info("Done")


if __name__ == '__main__':
    main()
