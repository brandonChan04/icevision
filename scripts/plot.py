import pandas as pd
import matplotlib.pyplot as plt
import sys

def plot_losses(csv_path):
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Define loss attributes to plot
    loss_attrs = [
        ('box_loss', 'train/box_loss', 'val/box_loss'),
        ('cls_loss', 'train/cls_loss', 'val/cls_loss'),
        ('dfl_loss', 'train/dfl_loss', 'val/dfl_loss')
    ]
    
    epochs = df['epoch']

    # Make a subplot for each loss type
    fig, axes = plt.subplots(1, len(loss_attrs), figsize=(16, 5))
    if len(loss_attrs) == 1:
        axes = [axes]
    
    for ax, (title, train_col, val_col) in zip(axes, loss_attrs):
        # Plot training loss
        ax.plot(epochs, df[train_col], label=f"Train {title}", marker='o')
        # Plot validation loss
        ax.plot(epochs, df[val_col], label=f"Val {title}", marker='x')
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.set_title(title)
        ax.legend()
        ax.grid(True)
    
    plt.tight_layout()
    plt.show()
    plt.savefig('losses_plot.png', dpi=300)

# Example usage:
# plot_losses("performance.csv")
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python plot_losses.py <path_to_csv>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    plot_losses(csv_path)