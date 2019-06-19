from .context import scared  # noqa: F401
import pytest
import numpy as np
from collections.abc import Iterable


SIZES_TO_TEST = [
    (1000, 25000),
    (1001, 5000),
    (5001, 2500),
    (10001, 1000),
    (50001, 250),
    (100001, 100)
]

BATCH_NUMBER = 10
LAST_BATCH_SIZE = 100


@pytest.fixture(params=SIZES_TO_TEST)
def thss(request):
    sizes = request.param
    shape = (BATCH_NUMBER * sizes[1] + LAST_BATCH_SIZE, sizes[0])
    samples = np.random.randint(0, 255, shape, dtype='uint8')
    plaintext = np.random.randint(0, 255, (shape[0], 16), dtype='uint8')
    return scared.traces.formats.read_ths_from_ram(samples=samples, plaintext=plaintext), sizes


@pytest.fixture
def ths():
    shape = (2000, 1000)
    samples = np.random.randint(0, 255, shape, dtype='uint8')
    plaintext = np.random.randint(0, 255, (shape[0], 16), dtype='uint8')
    return scared.traces.formats.read_ths_from_ram(samples=samples, plaintext=plaintext)


def test_container_raises_exception_if_ths_is_not_trace_header_set_compatible():
    with pytest.raises(TypeError):
        scared.Container(ths='foo')
    with pytest.raises(TypeError):
        scared.Container(ths=1235)
    with pytest.raises(TypeError):
        scared.Container(ths={})


def test_container_provides_iterator_on_traces_objects(thss):
    ths, sizes = thss
    container = scared.Container(ths)
    assert isinstance(container.batches(), Iterable)
    for batch in container.batches():
        assert batch.samples is not None
        assert batch.metadatas is not None
        assert len(batch) in (sizes[1], LAST_BATCH_SIZE)


def test_container_provides_trace_size_attribute(thss):
    ths, sizes = thss
    container = scared.Container(ths)
    assert container.trace_size == len(ths.samples[0, :])


def test_container_batches_accept_batch_size(thss):
    ths, sizes = thss
    container = scared.Container(ths)
    n_batch = len(ths) // 2000
    last_batch = len(ths) - 2000 * n_batch
    for batch in container.batches(batch_size=2000):
        if len(ths) < 2000:
            assert len(batch) == len(ths)
        else:
            assert len(batch) in (2000, last_batch)


def test_container_batches_raises_exception_if_batch_size_is_incorrect(ths):
    container = scared.Container(ths)
    with pytest.raises(TypeError):
        container.batches(batch_size='foo')
    with pytest.raises(ValueError):
        container.batches(batch_size=-12)


def test_container_raises_exception_if_frame_param_has_improper_type(ths):
    with pytest.raises(TypeError):
        scared.Container(ths, frame='foo')
    with pytest.raises(TypeError):
        scared.Container(ths, frame=2121.1)
    with pytest.raises(TypeError):
        scared.Container(ths, frame={})


def test_container_trace_size_use_frame(ths):
    cont = scared.Container(ths, frame=slice(None, 10))
    assert cont.trace_size == 10

    cont = scared.Container(ths, frame=slice(None, 2000))
    assert cont.trace_size == 1000

    cont = scared.Container(ths, frame=1)
    assert cont.trace_size == 1


def test_container_raises_error_if_bad_preprocesses(ths):
    with pytest.raises(TypeError):
        scared.Container(ths, preprocesses='foo')
    with pytest.raises(TypeError):
        scared.Container(ths, preprocesses=['foo', 123])
    with pytest.raises(TypeError):
        scared.Container(ths, preprocesses=134)


def test_container_with_one_preprocess(ths):
    @scared.preprocess
    def square(traces):
        return traces ** 2

    c = scared.Container(ths, preprocesses=square)
    b = c.batches(batch_size=10)[0]
    assert np.array_equal(b.samples, square(ths.samples[:10, :]))


def test_container_with_multiple_preprocess(ths):
    @scared.preprocess
    def square(traces):
        return traces ** 2

    @scared.preprocess
    def minus_2(traces):
        return (traces - 2).astype(traces.dtype)

    c = scared.Container(ths, preprocesses=[square, minus_2])
    b = c.batches(batch_size=10)[0]
    assert np.array_equal(b.samples, minus_2(square(ths.samples[:10, :])))


def test_container_with_frame(ths):
    c = scared.Container(ths, frame=slice(None, 20))
    b = c.batches(batch_size=10)[0]
    assert np.array_equal(b.samples, ths.samples[:10, :20])


def test_container_with_multiple_preprocess_and_frame(ths):
    @scared.preprocess
    def square(traces):
        return traces ** 2

    @scared.preprocess
    def minus_2(traces):
        return (traces - 2).astype(traces.dtype)

    c = scared.Container(ths, preprocesses=[square, minus_2], frame=slice(10, 30))
    b = c.batches(batch_size=10)[2]
    assert np.array_equal(b.samples, minus_2(square(ths.samples[20:30, 10:30])))
