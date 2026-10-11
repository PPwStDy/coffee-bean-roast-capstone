import os
import torch
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix

def test(dataloader, model, loss_fn, device, return_images=False):
    """
    Evaluates the model on the provided dataloader.
    Returns: loss, predictions, ground-truth labels, and optionally input images.
    """
    num_batches = len(dataloader)
    model.eval()

    loss = 0.0
    y_preds, y_trues = [], []
    images = []

    with torch.no_grad():
        for X, y in dataloader:
            X_dev, y_dev = X.to(device), y.to(device)
            pred = model(X_dev)
            y_pred = pred.argmax(dim=1)

            loss += loss_fn(pred, y_dev).item()
            y_preds.append(y_pred)
            y_trues.append(y_dev)
            if return_images:
                images.append(X.cpu())

    y_preds = torch.cat(y_preds)
    y_trues = torch.cat(y_trues)
    loss /= num_batches

    if return_images:
        images = torch.cat(images)
        return loss, y_preds, y_trues, images

    return loss, y_preds, y_trues


def plot_confusion_matrix(y_trues, y_preds, class_names, save_path='confusion_matrix.png'):
    """
    Generates and saves a confusion matrix heatmap.
    """
    cm = confusion_matrix(y_trues, y_preds)
    plt.figure(figsize=(7, 6))
    sns.heatmap(
        cm, 
        annot=True, 
        fmt='d', 
        cmap='YlOrBr', 
        xticklabels=class_names, 
        yticklabels=class_names,
        cbar=True
    )
    plt.title('Confusion Matrix - Coffee Bean Roast Level', fontsize=13, fontweight='bold', pad=12)
    plt.ylabel('Ground Truth Class', fontsize=11, fontweight='semibold')
    plt.xlabel('Predicted Class', fontsize=11, fontweight='semibold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


def get_classification_report(y_trues, y_preds, class_names):
    """
    Returns the scikit-learn text classification report.
    """
    return classification_report(y_trues, y_preds, target_names=class_names, digits=4)


def plot_misclassified_images(images, labels, preds, class_names, max_images=12, save_path='misclassified.png'):
    """
    Plots a grid of misclassified images for diagnostic analysis.
    """
    misclassified_idx = np.where(labels != preds)[0]
    if len(misclassified_idx) == 0:
        print("Perfect classification on test set! No misclassified images found.")
        return

    n_images = min(len(misclassified_idx), max_images)
    cols = min(3, n_images)
    rows = int(np.ceil(n_images / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 4 * rows))
    
    if rows == 1 and cols == 1:
        axes = np.array([axes])
    else:
        axes = np.array(axes).flatten()

    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])

    for i in range(n_images):
        idx = misclassified_idx[i]
        img = images[idx].permute(1, 2, 0).cpu().numpy()
        img = std * img + mean
        img = np.clip(img, 0, 1)

        axes[i].imshow(img)
        axes[i].set_title(f"True: {class_names[labels[idx]]}\nPred: {class_names[preds[idx]]}", color="red", fontsize=10)
        axes[i].axis('off')

    for j in range(n_images, len(axes)):
        axes[j].axis('off')

    plt.suptitle("Misclassified Test Samples Diagnostic", fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()


def plot_learning_curves(history, save_path='learning_curves.png'):
    """
    Plots training and validation loss, accuracy, and F1 trajectories.
    """
    epochs = range(1, len(history['train_loss']) + 1)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 4.5))

    # Loss
    ax1.plot(epochs, history['train_loss'], 'o-', label='Train Loss', color='#1f77b4', linewidth=2)
    ax1.plot(epochs, history['val_loss'], 's-', label='Val Loss', color='#ff7f0e', linewidth=2)
    ax1.set_title('Cross-Entropy Loss', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='best')

    # Accuracy
    ax2.plot(epochs, [a * 100 for a in history['train_acc']], 'o-', label='Train Acc', color='#1f77b4', linewidth=2)
    ax2.plot(epochs, [a * 100 for a in history['val_acc']], 's-', label='Val Acc', color='#2ca02c', linewidth=2)
    ax2.set_title('Accuracy (%)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy (%)')
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='best')

    # F1-Score
    ax3.plot(epochs, [f * 100 for f in history['train_f1']], 'o-', label='Train F1', color='#1f77b4', linewidth=2)
    ax3.plot(epochs, [f * 100 for f in history['val_f1']], 's-', label='Val F1', color='#d62728', linewidth=2)
    ax3.set_title('Macro F1-Score (%)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Epoch')
    ax3.set_ylabel('F1-Score (%)')
    ax3.grid(True, linestyle='--', alpha=0.5)
    ax3.legend(loc='best')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
