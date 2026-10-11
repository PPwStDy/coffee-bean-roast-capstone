import os
import sys
import argparse
from datetime import datetime
import torch
import torch.nn as nn
from torch.utils.tensorboard import SummaryWriter
from torcheval.metrics.functional import multiclass_accuracy, multiclass_f1_score

# Ensure local imports work whether run from root or Iteration4/
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from dataset import create_dataloaders, resolve_dataset_dir
from model import (
    PretrainedViT_B_16, 
    PretrainedSwinT, 
    PretrainedEfficientNetV2S, 
    PretrainedConvNeXtTiny
)
from dl_utils import (
    test, 
    plot_confusion_matrix, 
    get_classification_report, 
    plot_misclassified_images,
    plot_learning_curves
)

def train_model(
    model_name="swin",
    dataset_path="dataset",
    batch_size=32,
    epochs=20,
    backbone_lr=5e-5,
    head_lr=1e-3,
    patience=7,
    label_smoothing=0.05,
    output_dir=None
):
    if output_dir is None:
        output_dir = current_dir
    os.makedirs(output_dir, exist_ok=True)

    # 1. Device selection
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        # ConvNeXt backward pass has known view compatibility issue on MPS
        if model_name.lower() == "convnext":
            print("Note: ConvNeXt has a known view stride issue on macOS MPS. Falling back to CPU for ConvNeXt.")
            device = "cpu"
        else:
            device = "mps"
    else:
        device = "cpu"
    print(f"=== Running on device: {device} ===")

    # 2. Prepare DataLoaders
    train_dl, valid_dl, test_dl, class_names = create_dataloaders(
        dataset_dir=dataset_path,
        batch_size=batch_size,
        val_split=0.2,
        random_seed=42
    )
    num_classes = len(class_names)

    # 3. Model Initialization
    print(f"\nInitializing model: {model_name.upper()} for {num_classes} classes...")
    if model_name.lower() == "swin":
        model = PretrainedSwinT(num_classes=num_classes, fine_tune=True).to(device)
    elif model_name.lower() in ["efficientnet_v2_s", "effnet"]:
        model = PretrainedEfficientNetV2S(num_classes=num_classes, fine_tune=True).to(device)
    elif model_name.lower() == "vit":
        model = PretrainedViT_B_16(num_classes=num_classes, fine_tune=True).to(device)
    elif model_name.lower() == "convnext":
        model = PretrainedConvNeXtTiny(num_classes=num_classes, fine_tune=True).to(device)
    else:
        raise ValueError(f"Unknown model architecture: {model_name}. Choose from swin, efficientnet_v2_s, vit, convnext")

    # 4. Loss, Optimizer with Discriminative Learning Rates & OneCycleLR
    loss_fn = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

    # Discriminative parameter groups
    param_groups = model.get_param_groups(backbone_lr=backbone_lr, head_lr=head_lr, weight_decay=0.01)
    optimizer = torch.optim.AdamW(param_groups)

    max_lrs = [backbone_lr * 4, head_lr * 2.5]
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer,
        max_lr=max_lrs,
        steps_per_epoch=len(train_dl),
        epochs=epochs,
        pct_start=0.2
    )

    # 5. TensorBoard Setup
    runs_dir = os.path.join(output_dir, "runs")
    log_name = f"trainer_{model._get_name()}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    writer = SummaryWriter(os.path.join(runs_dir, log_name))

    # 6. Training Loop with History Tracking & Early Stopping
    best_vloss = float("inf")
    epochs_no_improve = 0
    checkpoint_path = os.path.join(output_dir, f"model_best_vloss_{model_name.lower()}.pth")

    history = {
        'train_loss': [],
        'val_loss': [],
        'train_acc': [],
        'val_acc': [],
        'train_f1': [],
        'val_f1': []
    }

    print("\n" + "=" * 60)
    print(f"Starting Training: {model._get_name()} ({epochs} epochs, batch_size={batch_size})")
    print(f"Learning rates -> Backbone: {backbone_lr}, Head: {head_lr}")
    print("=" * 60)

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0

        for X, y in train_dl:
            X, y = X.to(device), y.to(device).long()
            optimizer.zero_grad()
            pred = model(X)
            loss = loss_fn(pred, y)
            loss.backward()
            optimizer.step()
            scheduler.step()
            running_loss += loss.item()

        avg_train_loss = running_loss / len(train_dl)

        # Evaluation on Train and Validation sets
        _, train_preds, train_trues = test(train_dl, model, loss_fn, device)
        val_loss, val_preds, val_trues = test(valid_dl, model, loss_fn, device)

        train_acc = multiclass_accuracy(train_preds.cpu(), train_trues.cpu(), num_classes=num_classes).item()
        val_acc = multiclass_accuracy(val_preds.cpu(), val_trues.cpu(), num_classes=num_classes).item()

        train_f1 = multiclass_f1_score(train_preds.cpu(), train_trues.cpu(), num_classes=num_classes, average="macro").item()
        val_f1 = multiclass_f1_score(val_preds.cpu(), val_trues.cpu(), num_classes=num_classes, average="macro").item()

        # Update history
        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(val_loss)
        history['train_acc'].append(train_acc)
        history['val_acc'].append(val_acc)
        history['train_f1'].append(train_f1)
        history['val_f1'].append(val_f1)

        print(
            f"Epoch [{epoch+1:02d}/{epochs:02d}] "
            f"Train Loss: {avg_train_loss:.4f} | Train Acc: {train_acc*100:5.2f}% | "
            f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:5.2f}% | Val F1: {val_f1*100:5.2f}%"
        )

        # Log to TensorBoard
        writer.add_scalars("Loss", {"train": avg_train_loss, "val": val_loss}, epoch)
        writer.add_scalars("Accuracy", {"train": train_acc, "val": val_acc}, epoch)
        writer.add_scalars("F1_Macro", {"train": train_f1, "val": val_f1}, epoch)

        # Checkpoint based on best validation loss
        if val_loss < best_vloss:
            best_vloss = val_loss
            torch.save(model.state_dict(), checkpoint_path)
            print(f"  * Saved new best checkpoint to {checkpoint_path} (val_loss: {val_loss:.4f}, val_acc: {val_acc*100:.2f}%)")
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"\n[Early Stopping] No improvement in validation loss for {patience} consecutive epochs. Stopping at epoch {epoch+1}.")
                break

    writer.close()
    print("\nTraining completed successfully!")

    # 7. Save Learning Curves
    curves_path = os.path.join(output_dir, f"learning_curves_{model_name.lower()}.png")
    plot_learning_curves(history, save_path=curves_path)
    print(f"Saved learning curves to: {curves_path}")

    # 8. Final Evaluation on Independent Test Set (400 samples)
    print("\n" + "=" * 60)
    print(f"Evaluating Best {model._get_name()} on Independent Test Set (400 samples)")
    print("=" * 60)

    # Reload best weights
    model.load_state_dict(torch.load(checkpoint_path, weights_only=True))
    test_loss, test_preds, test_trues, test_images = test(
        test_dl, model, loss_fn, device, return_images=True
    )

    test_acc = multiclass_accuracy(test_preds.cpu(), test_trues.cpu(), num_classes=num_classes).item()
    test_f1_macro = multiclass_f1_score(test_preds.cpu(), test_trues.cpu(), num_classes=num_classes, average="macro").item()
    test_f1_micro = multiclass_f1_score(test_preds.cpu(), test_trues.cpu(), num_classes=num_classes, average="micro").item()

    print(f"\nFinal Test Results:")
    print(f"  Test Loss:       {test_loss:.4f}")
    print(f"  Test Accuracy:   {test_acc * 100:.2f}%")
    print(f"  Test Macro F1:   {test_f1_macro * 100:.2f}%")
    print(f"  Test Micro F1:   {test_f1_micro * 100:.2f}%")

    # Classification Report
    y_true_np = test_trues.cpu().numpy()
    y_pred_np = test_preds.cpu().numpy()
    report = get_classification_report(y_true_np, y_pred_np, class_names)
    print("\nClassification Report (Test Set):")
    print(report)

    # Save Confusion Matrix Heatmap
    cm_path = os.path.join(output_dir, f"confusion_matrix_{model_name.lower()}.png")
    plot_confusion_matrix(y_true_np, y_pred_np, class_names, save_path=cm_path)
    print(f"Saved confusion matrix heatmap to: {cm_path}")

    # Save Misclassified Images Diagnostic
    misc_path = os.path.join(output_dir, f"misclassified_{model_name.lower()}.png")
    plot_misclassified_images(test_images, y_true_np, y_pred_np, class_names, save_path=misc_path)
    print(f"Saved misclassified sample analysis to: {misc_path}")

    # Save Detailed Summary Report
    summary_path = os.path.join(output_dir, f"test_summary_{model_name.lower()}.txt")
    with open(summary_path, "w") as f:
        f.write(f"Coffee Bean Roast Level Classification - Iteration 4\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Model Architecture: {model._get_name()}\n")
        f.write(f"Best Val Loss: {best_vloss:.4f}\n")
        f.write(f"Test Loss: {test_loss:.4f}\n")
        f.write(f"Test Accuracy: {test_acc * 100:.2f}%\n")
        f.write(f"Test Macro F1: {test_f1_macro * 100:.2f}%\n")
        f.write(f"Test Micro F1: {test_f1_micro * 100:.2f}%\n\n")
        f.write("Per-Class Classification Report:\n")
        f.write(report)
    print(f"Saved test summary report to: {summary_path}")

    return {
        "model": model._get_name(),
        "best_vloss": best_vloss,
        "test_loss": test_loss,
        "test_accuracy": test_acc,
        "test_f1_macro": test_f1_macro,
        "checkpoint": checkpoint_path,
        "confusion_matrix": cm_path,
        "learning_curves": curves_path,
        "misclassified": misc_path
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train coffee bean roast classification model - Iteration 4")
    parser.add_argument("--model", type=str, default="swin", choices=["swin", "efficientnet_v2_s", "effnet", "vit", "convnext"], help="Model architecture")
    parser.add_argument("--dataset", type=str, default="dataset", help="Path to dataset directory")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs")
    parser.add_argument("--backbone_lr", type=float, default=5e-5, help="Backbone learning rate")
    parser.add_argument("--head_lr", type=float, default=1e-3, help="Classification head learning rate")
    parser.add_argument("--patience", type=int, default=7, help="Early stopping patience")
    parser.add_argument("--label_smoothing", type=float, default=0.05, help="Label smoothing epsilon")
    parser.add_argument("--output_dir", type=str, default=None, help="Output directory for checkpoints and plots")
    args = parser.parse_args()

    train_model(
        model_name=args.model,
        dataset_path=args.dataset,
        batch_size=args.batch_size,
        epochs=args.epochs,
        backbone_lr=args.backbone_lr,
        head_lr=args.head_lr,
        patience=args.patience,
        label_smoothing=args.label_smoothing,
        output_dir=args.output_dir
    )
