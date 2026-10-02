import pytest
from elmetron.runtime import InstanceLock


def test_single_instance_lock_and_release(tmp_path):
    path=tmp_path/'instance.lock'
    with InstanceLock(path):
        with pytest.raises(RuntimeError,match='already using'):
            with InstanceLock(path): pass
    with InstanceLock(path): pass
