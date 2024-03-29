# Copyright © 2023 Apple Inc.

import math
import unittest

import mlx.core as mx
import mlx_tests


class TestRandom(mlx_tests.MLXTestCase):
    def test_global_rng(self):
        mx.random.seed(3)
        a = mx.random.uniform()
        b = mx.random.uniform()

        mx.random.seed(3)
        x = mx.random.uniform()
        y = mx.random.uniform()

        self.assertEqual(a.item(), x.item())
        self.assertEqual(y.item(), b.item())

    def test_key(self):
        k1 = mx.random.key(0)
        k2 = mx.random.key(0)
        self.assertTrue(mx.array_equal(k1, k2))

        k2 = mx.random.key(1)
        self.assertFalse(mx.array_equal(k1, k2))

    def test_key_split(self):
        key = mx.random.key(0)

        k1, k2 = mx.random.split(key)
        self.assertFalse(mx.array_equal(k1, k2))

        r1, r2 = mx.random.split(key)
        self.assertTrue(mx.array_equal(k1, r1))
        self.assertTrue(mx.array_equal(k2, r2))

        keys = mx.random.split(key, 10)
        self.assertEqual(keys.shape, (10, 2))

    def test_uniform(self):
        key = mx.random.key(0)
        a = mx.random.uniform(key=key)
        self.assertEqual(a.shape, ())
        self.assertEqual(a.dtype, mx.float32)

        b = mx.random.uniform(key=key)
        self.assertEqual(a.item(), b.item())

        a = mx.random.uniform(shape=(2, 3))
        self.assertEqual(a.shape, (2, 3))

        a = mx.random.uniform(shape=(1000,), low=-1, high=5)
        self.assertTrue(mx.all((a > -1) < 5).item())

        a = mx.random.uniform(shape=(1000,), low=mx.array(-1), high=5)
        self.assertTrue(mx.all((a > -1) < 5).item())

        a = mx.random.uniform(low=-0.1, high=0.1, shape=(1,), dtype=mx.bfloat16)
        self.assertEqual(a.dtype, mx.bfloat16)

        self.assertEqual(mx.random.uniform().dtype, mx.random.uniform(dtype=None).dtype)

    def test_normal(self):
        key = mx.random.key(0)
        a = mx.random.normal(key=key)
        self.assertEqual(a.shape, ())
        self.assertEqual(a.dtype, mx.float32)

        b = mx.random.normal(key=key)
        self.assertEqual(a.item(), b.item())

        a = mx.random.normal(shape=(2, 3))
        self.assertEqual(a.shape, (2, 3))

        ## Generate in float16 or bfloat16
        for t in [mx.float16, mx.bfloat16]:
            a = mx.random.normal(dtype=t)
            self.assertEqual(a.dtype, t)

        # Generate with a given mean and standard deviation
        loc = 1.0
        scale = 2.0

        a = mx.random.normal(shape=(3, 2), loc=loc, scale=scale, key=key)
        b = scale * mx.random.normal(shape=(3, 2), key=key) + loc
        self.assertTrue(mx.allclose(a, b))

        a = mx.random.normal(
            shape=(3, 2), loc=loc, scale=scale, dtype=mx.float16, key=key
        )
        b = scale * mx.random.normal(shape=(3, 2), dtype=mx.float16, key=key) + loc
        self.assertTrue(mx.allclose(a, b))

        self.assertEqual(mx.random.normal().dtype, mx.random.normal(dtype=None).dtype)
        
        # Test not getting -inf or inf with half precison
        for hp in [mx.float16, mx.bfloat16]:
            a = abs(mx.random.normal(shape=(10000,), loc=0, scale=1, dtype=hp))
            self.assertTrue(mx.all(a < mx.inf))

    def test_multivariate_normal(self):
        key = mx.random.key(0)
        mean = mx.array([0, 0])
        cov = mx.array([[1, 0], [0, 1]])

        a = mx.random.multivariate_normal(mean, cov, key=key, stream=mx.cpu)
        self.assertEqual(a.shape, (2,))
        self.assertEqual(a.dtype, mx.float32)

        ## Check dtypes
        for t in [mx.float32]:
            a = mx.random.multivariate_normal(
                mean, cov, dtype=t, key=key, stream=mx.cpu
            )
            self.assertEqual(a.dtype, t)
        for t in [
            mx.int8,
            mx.int32,
            mx.int64,
            mx.uint8,
            mx.uint32,
            mx.uint64,
            mx.float16,
            mx.bfloat16,
        ]:
            with self.assertRaises(ValueError):
                mx.random.multivariate_normal(
                    mean, cov, dtype=t, key=key, stream=mx.cpu
                )

        ## Check incompatibel shapes
        with self.assertRaises(ValueError):
            mean = mx.zeros((2, 2))
            cov = mx.zeros((2, 2))
            mx.random.multivariate_normal(mean, cov, key=key, stream=mx.cpu)

        with self.assertRaises(ValueError):
            mean = mx.zeros((3,))
            cov = mx.zeros((2, 2))
            mx.random.multivariate_normal(mean, cov, key=key, stream=mx.cpu)

        with self.assertRaises(ValueError):
            mean = mx.zeros((2,))
            cov = mx.zeros((2, 3))
            mx.random.multivariate_normal(mean, cov, key=key, stream=mx.cpu)

        ## Check correcteness of the mean and covariance
        n_test = int(1e7)

        def check_jointly_gaussian(data, mean, cov):
            empirical_mean = mx.mean(data, axis=0)
            empirical_cov = (
                (data - empirical_mean).T @ (data - empirical_mean) / data.shape[0]
            )
            N = data.shape[1]
            self.assertTrue(
                mx.allclose(
                    empirical_mean, mean, rtol=0.0, atol=10 * N**2 / math.sqrt(n_test)
                )
            )
            self.assertTrue(
                mx.allclose(
                    empirical_cov, cov, rtol=0.0, atol=10 * N**2 / math.sqrt(n_test)
                )
            )

        mean = mx.array([4, 7])
        cov = mx.array([[2, 0.5], [0.5, 1]])
        data = mx.random.multivariate_normal(
            mean, cov, shape=(n_test,), key=key, stream=mx.cpu
        )
        check_jointly_gaussian(data, mean, cov)

        mean = mx.arange(3)
        cov = mx.array([[1, -1, 0.5], [-1, 1, -0.5], [0.5, -0.5, 1]])
        data = mx.random.multivariate_normal(
            mean, cov, shape=(n_test,), key=key, stream=mx.cpu
        )
        check_jointly_gaussian(data, mean, cov)

    def test_randint(self):
        a = mx.random.randint(0, 1, [])
        self.assertEqual(a.shape, ())
        self.assertEqual(a.dtype, mx.int32)

        shape = (88,)
        low = mx.array(3)
        high = mx.array(15)

        key = mx.random.key(0)
        a = mx.random.randint(low, high, shape, key=key)
        self.assertEqual(a.shape, shape)
        self.assertEqual(a.dtype, mx.int32)

        # Check using the same key yields the same value
        b = mx.random.randint(low, high, shape, key=key)
        self.assertListEqual(a.tolist(), b.tolist())

        shape = (3, 4)
        low = mx.reshape(mx.array([0] * 3), [3, 1])
        high = mx.reshape(mx.array([12, 13, 14, 15]), [1, 4])

        a = mx.random.randint(low, high, shape)
        self.assertEqual(a.shape, shape)

        a = mx.random.randint(-10, 10, [1000, 1000])
        self.assertTrue(mx.all(-10 <= a).item() and mx.all(a < 10).item())

        a = mx.random.randint(10, -10, [1000, 1000])
        self.assertTrue(mx.all(a == 10).item())

        self.assertEqual(
            mx.random.randint(0, 1).dtype, mx.random.randint(0, 1, dtype=None).dtype
        )

    def test_bernoulli(self):
        a = mx.random.bernoulli()
        self.assertEqual(a.shape, ())
        self.assertEqual(a.dtype, mx.bool_)

        a = mx.random.bernoulli(mx.array(0.5), [5])
        self.assertEqual(a.shape, (5,))

        a = mx.random.bernoulli(mx.array([2.0, -2.0]))
        self.assertEqual(a.tolist(), [True, False])
        self.assertEqual(a.shape, (2,))

        p = mx.array([0.1, 0.2, 0.3])
        mx.reshape(p, [1, 3])
        x = mx.random.bernoulli(p, [4, 3])
        self.assertEqual(x.shape, (4, 3))

        with self.assertRaises(ValueError):
            mx.random.bernoulli(p, [2])  # Bad shape

        with self.assertRaises(ValueError):
            mx.random.bernoulli(0, [2])  # Bad type

    def test_truncated_normal(self):
        a = mx.random.truncated_normal(-2.0, 2.0)
        self.assertEqual(a.size, 1)
        self.assertEqual(a.dtype, mx.float32)

        a = mx.random.truncated_normal(mx.array([]), mx.array([]))
        self.assertEqual(a.dtype, mx.float32)
        self.assertEqual(a.size, 0)

        lower = mx.reshape(mx.array([-2.0, 0.0]), [1, 2])
        upper = mx.reshape(mx.array([0.0, 1.0, 2.0]), [3, 1])
        a = mx.random.truncated_normal(lower, upper)

        self.assertEqual(a.shape, (3, 2))
        self.assertTrue(mx.all(lower <= a).item() and mx.all(a <= upper).item())

        a = mx.random.truncated_normal(2.0, -2.0)
        self.assertTrue(mx.all(a == 2.0).item())

        a = mx.random.truncated_normal(-3.0, 3.0, [542, 399])
        self.assertEqual(a.shape, (542, 399))

        lower = mx.array([-2.0, -1.0])
        higher = mx.array([1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            mx.random.truncated_normal(lower, higher)  # Bad shape

        self.assertEqual(
            mx.random.truncated_normal(0, 1).dtype,
            mx.random.truncated_normal(0, 1, dtype=None).dtype,
        )

    def test_gumbel(self):
        samples = mx.random.gumbel(shape=(100, 100))
        self.assertEqual(samples.shape, (100, 100))
        self.assertEqual(samples.dtype, mx.float32)
        mean = 0.5772
        # Std deviation of the sample mean is small (<0.02),
        # so this test is pretty conservative
        self.assertTrue(mx.abs(mx.mean(samples) - mean) < 0.2)

        self.assertEqual(
            mx.random.gumbel((1, 1)).dtype, mx.random.gumbel((1, 1), dtype=None).dtype
        )

    def test_categorical(self):
        logits = mx.zeros((10, 20))
        self.assertEqual(mx.random.categorical(logits, -1).shape, (10,))
        self.assertEqual(mx.random.categorical(logits, 0).shape, (20,))
        self.assertEqual(mx.random.categorical(logits, 1).shape, (10,))

        out = mx.random.categorical(logits)
        self.assertEqual(out.shape, (10,))
        self.assertEqual(out.dtype, mx.uint32)
        self.assertTrue(mx.max(out).item() < 20)

        out = mx.random.categorical(logits, 0, [5, 20])
        self.assertEqual(out.shape, (5, 20))
        self.assertTrue(mx.max(out).item() < 10)

        out = mx.random.categorical(logits, 1, num_samples=7)
        self.assertEqual(out.shape, (10, 7))
        out = mx.random.categorical(logits, 0, num_samples=7)
        self.assertEqual(out.shape, (20, 7))

        with self.assertRaises(ValueError):
            mx.random.categorical(logits, shape=[10, 5], num_samples=5)


if __name__ == "__main__":
    unittest.main()
