"""Contract and ownership checks execute without real cloud mutations."""
import inspect
import pytest
from cloudlayer.adapter import AzureCloudAdapter
from cloudlayer.base import CloudAdapter, StorageAdapter
from cloudlayer.config import SLOTS
from cloudlayer.teardown import teardown


def test_cloud_interface_complete():
    expected={'upload','download','push_image','submit_training','wait_training','register_model','deploy','invoke','emit_metric','teardown'}
    assert CloudAdapter.__abstractmethods__==expected
    assert not inspect.isabstract(AzureCloudAdapter)
    assert StorageAdapter.__abstractmethods__=={'download_file','upload_file'}
    assert len(SLOTS)==8


def test_generation_explicitly_optional():
    adapter=AzureCloudAdapter({'PROJECT_ID':'test','AZURE_ML_WORKSPACE':'shared','AZURE_ML_RESOURCE_GROUP':'shared'})
    with pytest.raises(NotImplementedError,match='Optional'):
        adapter.generate('unused',{})


def test_teardown_rejects_shared_group_before_cli():
    with pytest.raises(ValueError,match='only the approved'):
        teardown({'PROJECT_ID':'itcs355-6688218'}, {'course':'itcs355','student':'6688218','lab':'capstone'})


def test_deploy_requires_digest_and_allocation():
    adapter=AzureCloudAdapter({'PROJECT_ID':'test','AZURE_ML_WORKSPACE':'shared','AZURE_ML_RESOURCE_GROUP':'shared'})
    with pytest.raises(ValueError,match='immutable'):
        adapter.deploy('image:latest','endpoint','2cpu-4Gi')
    with pytest.raises(ValueError,match='allocation'):
        adapter.deploy('image:latest','endpoint','1cpu-2Gi')
