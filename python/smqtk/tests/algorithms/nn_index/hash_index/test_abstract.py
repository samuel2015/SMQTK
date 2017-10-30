import mock
import unittest

import six

from smqtk.algorithms.nn_index.hash_index import HashIndex, get_hash_index_impls


class DummyHI (HashIndex):

    @classmethod
    def is_usable(cls):
        return True

    def get_config(self):
        return {}

    def count(self):
        return 0

    def _build_index(self, hashes):
        return

    def _update_index(self, hashes):
        return

    def _nn(self, h, n=1):
        return


class TestHashIndex (unittest.TestCase):

    def test_get_impls(self):
        m = get_hash_index_impls()
        self.assertIsInstance(m, dict)
        for cls in six.itervalues(m):
            self.assertTrue(issubclass(cls, HashIndex))

    def test_build_index_empty_iter(self):
        idx = DummyHI()
        idx._build_index = mock.MagicMock()
        self.assertRaisesRegexp(
            ValueError,
            str(HashIndex._empty_iterable_exception()),
            idx.build_index, []
        )
        # Internal method should not have been called
        idx._build_index.assert_not_called()

    def test_build_index_with_values(self):
        idx = DummyHI()
        idx._build_index = mock.MagicMock()
        # No error should be returned. Returned iterable contents should match
        # input values.
        idx.build_index([0, 1, 2])
        self.assertSetEqual(
            set(idx._build_index.call_args[0][0]),
            {0, 1, 2}
        )

    def test_update_index_empty_iter(self):
        idx = DummyHI()
        idx._update_index = mock.MagicMock()
        self.assertRaisesRegexp(
            ValueError,
            "No hash vectors.*",
            idx.update_index, []
        )
        # Internal method should not have been called.
        idx._update_index.assert_not_called()

    def test_update_index_with_values(self):
        idx = DummyHI()
        idx._update_index = mock.MagicMock()
        # No error should be returned. Returned iterable contents should match
        # input values.
        idx.update_index([0, 1, 2])
        self.assertSetEqual(
            set(idx._update_index.call_args[0][0]),
            {0, 1, 2}
        )

    def test_nn_no_index(self):
        idx = DummyHI()
        idx._nn = mock.MagicMock()
        self.assertRaises(
            ValueError,
            idx.nn, 'something'
        )
        # Internal method should not have been called.
        idx._nn.assert_not_called()

    def test_nn_has_count(self):
        idx = DummyHI()
        idx.count = mock.MagicMock()
        idx.count.return_value = 10
        idx._nn = mock.MagicMock()
        # This call should now pass that count returns something greater than 0.
        idx.nn('dummy')
        idx._nn.assert_called_with("dummy", 1)

        idx.nn('bar', 10)
        idx._nn.assert_called_with("bar", 10)
