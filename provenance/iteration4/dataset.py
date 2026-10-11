import os
import torch
from torch.utils.data import Dataset, DataLoader, Subset
from torchvision.datasets import ImageFolder
import torchvision.transforms.v2 as transforms_v2
from sklearn.model_selection import StratifiedShuffleSplit

# Normalization constants (ImageNet standard)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Data Augmentations for Training - Color-preserving for Roast Classification
def get_train_transforms(img_size=224):
    return transforms_v2.Compose([
        transforms_v2.RandomResizedCrop(img_size, scale=(0.85, 1.0), antialias=True),
        transforms_v2.RandomHorizontalFlip(p=0.5),
        transforms_v2.RandomVerticalFlip(p=0.5),
        transforms_v2.RandomRotation(degrees=180),
        transforms_v2.ToImage(),
        transforms_v2.ToDtype(torch.float32, scale=True),
        transforms_v2.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

# Deterministic Transforms for Validation & Testing
def get_eval_transforms(img_size=224):
    return transforms_v2.Compose([
        transforms_v2.Resize((img_size, img_size), antialias=True),
        transforms_v2.ToImage(),
        transforms_v2.ToDtype(torch.float32, scale=True),
        transforms_v2.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


class TransformedSubset(Dataset):
    """
    Applies a specific transform to a subset of an ImageFolder dataset.
    This guarantees train and validation subsets can use different augmentations.
    """
    def __init__(self, subset, transform=None):
        self.subset = subset
        self.transform = transform

    def __getitem__(self, idx):
        x, y = self.subset[idx]
        if self.transform:
            x = self.transform(x)
        return x, y

    def __len__(self):
        return len(self.subset)


def resolve_dataset_dir(dataset_dir="dataset"):
    """
    Automatically resolves the coffee bean roast dataset directory across different execution contexts.
    """
    candidates = [
        dataset_dir,
        os.path.abspath(dataset_dir),
        os.path.join(os.getcwd(), dataset_dir),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dataset"),
        "dataset",
        "../dataset",
        "/app/dataset"
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.path.exists(os.path.join(c, "train")):
            return os.path.abspath(c)
    raise FileNotFoundError(f"Dataset directory not found in candidates: {candidates}")


def create_dataloaders(dataset_dir="dataset", batch_size=32, val_split=0.2, random_seed=42, num_workers=0):
    """
    Creates stratified train, val, and test DataLoaders for the Coffee Bean Roast dataset.
    """
    resolved_path = resolve_dataset_dir(dataset_dir)
    train_dir = os.path.join(resolved_path, "train")
    test_dir = os.path.join(resolved_path, "test")

    # Base dataset without transforms so we can apply specific transforms to train vs val subsets
    base_train_ds = ImageFolder(train_dir)
    test_raw_ds = ImageFolder(test_dir)

    class_names = base_train_ds.classes
    targets = [target for _, target in base_train_ds.samples]

    # Stratified split to ensure equal class proportions in train and validation sets
    sss = StratifiedShuffleSplit(n_splits=1, test_size=val_split, random_state=random_seed)
    train_indices, val_indices = next(sss.split(range(len(targets)), targets))

    raw_train_subset = Subset(base_train_ds, train_indices)
    raw_val_subset = Subset(base_train_ds, val_indices)

    # Wrap subsets with appropriate augmentations
    train_dataset = TransformedSubset(raw_train_subset, transform=get_train_transforms())
    val_dataset = TransformedSubset(raw_val_subset, transform=get_eval_transforms())
    test_dataset = TransformedSubset(test_raw_ds, transform=get_eval_transforms())

    print(f"Dataset path: {resolved_path}")
    print(f"Dataset summary:")
    print(f"  Classes: {class_names}")
    print(f"  Training samples:   {len(train_dataset)}")
    print(f"  Validation samples: {len(val_dataset)}")
    print(f"  Test samples:       {len(test_dataset)}")

    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
    val_loader = DataLoader(
        val_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        num_workers=num_workers
    )
    test_loader = DataLoader(
        test_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        num_workers=num_workers
    )

    return train_loader, val_loader, test_loader, class_names
