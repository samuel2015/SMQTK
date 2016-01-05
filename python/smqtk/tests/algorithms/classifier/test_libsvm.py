import unittest

import multiprocessing
import multiprocessing.pool
import nose.tools as ntools
import numpy

from smqtk.algorithms.classifier.libsvm import LibSvmClassifier
from smqtk.representation import \
    ClassificationElementFactory, \
    DescriptorElementFactory
from smqtk.representation.classification_element.memory import \
    MemoryClassificationElement
from smqtk.representation.descriptor_element.local_elements import \
    DescriptorMemoryElement


if LibSvmClassifier.is_usable():

    class TestLibSvmClassifier (unittest.TestCase):

        def test_simple_classification(self):
            """
            Test libSVM classification functionality using random constructed
            data, training the y=0.5 split
            """
            DIM = 2
            N = 1000
            POS_LABEL = 'positive'
            p = multiprocessing.pool.ThreadPool()
            d_factory = DescriptorElementFactory(DescriptorMemoryElement, {})
            c_factory = ClassificationElementFactory(MemoryClassificationElement, {})

            def make_element((i, v)):
                d = d_factory.new_descriptor('test', i)
                d.set_vector(v)
                return d

            # Constructing artificial descriptors
            x = numpy.random.rand(N, DIM)
            x_pos = x[x[:, 1] <= 0.45]
            x_neg = x[x[:, 1] >= 0.55]

            d_pos = p.map(make_element, enumerate(x_pos))
            d_neg = p.map(make_element, enumerate(x_neg, start=N//2))

            # Create/Train test classifier
            classifier = LibSvmClassifier(
                train_params={
                    '-t': 0,  # linear kernel
                    '-b': 1,  # enable probability estimates
                    '-c': 2,  # SVM-C parameter C
                    '-q': '',  # quite mode
                },
                normalize=None,  # DO NOT normalize descriptors
            )
            classifier.train({POS_LABEL: d_pos}, d_neg)

            # Test classifier
            x = numpy.random.rand(N, DIM)
            x_pos = x[x[:, 1] <= 0.45]
            x_neg = x[x[:, 1] >= 0.55]

            d_pos = p.map(make_element, enumerate(x_pos, N))
            d_neg = p.map(make_element, enumerate(x_neg, N + N//2))

            for d in d_pos:
                c = classifier.classify(d, c_factory)
                ntools.assert_equal(c.max_label(),
                                    POS_LABEL,
                                    "Found False positive: %s :: %s" %
                                    (d.vector(), c.get_classification()))
            for d in d_neg:
                c = classifier.classify(d, c_factory)
                ntools.assert_equal(c.max_label(),
                                    LibSvmClassifier.NEGATIVE_LABEL,
                                    "Found False negative: %s :: %s" %
                                    (d.vector(), c.get_classification()))

            # Closing resources
            p.close()
            p.join()
