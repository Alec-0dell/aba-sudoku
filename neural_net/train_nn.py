import os
import glob
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# --- Hyperparameters & Configuration ---
BS, LR, EPOCHS, PATIENCE = 64, 5e-4, 20, 3
EMBED_DIM, NUM_HEADS, NUM_LAYERS, DIM_FF = 256, 8, 2, 512
STEPS = 4  # Recurrent iteration depth
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATA_DIR = os.path.join(os.path.dirname(__file__), "processed_data")


# --- Data Pipeline ---
def load_datasets():
    """Loads and splits all available difficulty tiers from disk."""
    datasets = {}
    for tier in ["easy", "medium", "hard", "diabolical"]:
        f_path = os.path.join(DATA_DIR, f"solved_{tier}.txt")
        if not os.path.exists(f_path):
            continue

        x_tier, y_tier = [], []
        with open(f_path, "r") as f:
            lines = [line.strip().split(",") for line in f if "," in line.strip()]
            x_tier.extend([[int(c) for c in inp] for inp, _ in lines])
            y_tier.extend([[int(c) - 1 for c in tar] for _, tar in lines])

        datasets[tier] = (torch.tensor(x_tier), torch.tensor(y_tier))

    return datasets


def build_validation_set(datasets):
    """Extracts the final 20% of each loaded tier for a global validation set."""
    x_val = torch.cat([datasets[t][0][int(0.8 * len(datasets[t][0])):] for t in datasets]).to(DEVICE)
    y_val = torch.cat([datasets[t][1][int(0.8 * len(datasets[t][1])):] for t in datasets]).to(DEVICE)
    return x_val, y_val


def get_curriculum_data(epoch, datasets):
    """Dynamically expands the active dataset pool based on the current epoch."""
    active_tiers = []
    if epoch >= 1: active_tiers.append("easy")
    if epoch >= 4: active_tiers.append("medium")
    if epoch >= 7: active_tiers.append("hard")
    if epoch >= 10: active_tiers.append("diabolical")

    x_list, y_list = [], []
    for tier in active_tiers:
        if tier in datasets:
            x_list.append(datasets[tier][0][:int(0.8 * len(datasets[tier][0]))])
            y_list.append(datasets[tier][1][:int(0.8 * len(datasets[tier][1]))])

    return torch.cat(x_list), torch.cat(y_list), active_tiers[-1]


# --- Model Architecture ---
def generate_sudoku_mask():
    """Creates an 81x81 mask enforcing strict row, column, and 3x3 box attention bounds."""
    mask = torch.full((81, 81), float('-inf'))
    for i in range(81):
        r1, c1 = i // 9, i % 9
        b1 = (r1 // 3) * 3 + (c1 // 3)
        for j in range(81):
            r2, c2 = j // 9, j % 9
            b2 = (r2 // 3) * 3 + (c2 // 3)
            if r1 == r2 or c1 == c2 or b1 == b2:
                mask[i, j] = 0.0
    return mask


class RecurrentSudokuTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        # Positional & Spatial Embeddings
        self.embedding = nn.Embedding(10, EMBED_DIM)
        self.row_embed = nn.Embedding(9, EMBED_DIM)
        self.col_embed = nn.Embedding(9, EMBED_DIM)
        self.box_embed = nn.Embedding(9, EMBED_DIM)

        # Coordinate buffers
        self.register_buffer("row_idx", torch.arange(81) // 9)
        self.register_buffer("col_idx", torch.arange(81) % 9)
        self.register_buffer("box_idx", (torch.arange(81) // 27) * 3 + ((torch.arange(81) % 9) // 3))
        self.register_buffer("attn_mask", generate_sudoku_mask())

        # Core Transformer & Projections
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=EMBED_DIM, nhead=NUM_HEADS, dim_feedforward=DIM_FF,
            activation="relu", batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=NUM_LAYERS)
        self.classifier = nn.Linear(EMBED_DIM, 9)
        self.prediction_projection = nn.Linear(9, EMBED_DIM)

    def forward(self, x, steps=STEPS):
        pos = self.row_embed(self.row_idx) + self.col_embed(self.col_idx) + self.box_embed(self.box_idx)
        h = self.embedding(x) + pos.unsqueeze(0)

        all_logits = []
        for _ in range(steps):
            # Attend within peer boundaries
            h = self.transformer(h, mask=self.attn_mask)

            # Extract intermediate predictions
            logits = self.classifier(h)
            all_logits.append(logits)

            # Project predictions back into latent space for the next iteration
            probs = torch.softmax(logits, dim=-1)
            h = h + self.prediction_projection(probs)

        return all_logits


# --- Training Routines ---
def train_epoch(model, loader, optimizer, criterion):
    """Executes one pass over the data, applying loss at every recurrent step."""
    model.train()
    for x, y in loader:
        optimizer.zero_grad()
        x_dev, y_dev = x.to(DEVICE), y.to(DEVICE)

        step_outputs = model(x_dev)

        total_loss = 0
        for out in step_outputs:
            base_loss = criterion(out.view(-1, 9), y_dev.view(-1))

            # Penalize alterations to immutable starting clues
            given_mask = (x_dev != 0).view(-1)
            given_loss = criterion(out.view(-1, 9)[given_mask], y_dev.view(-1)[given_mask])

            total_loss += base_loss + 5.0 * given_loss

        loss = total_loss / len(step_outputs)
        loss.backward()
        optimizer.step()


def evaluate(model, x_val, y_val, criterion):
    """Evaluates global validation metrics using the final recurrent step's output."""
    model.eval()
    with torch.no_grad():
        step_outputs = model(x_val)
        final_out = step_outputs[-1]

        val_loss = criterion(final_out.view(-1, 9), y_val.view(-1)).item()
        preds = torch.argmax(final_out, dim=-1)
        acc = (preds == y_val).float().mean().item() * 100

    return val_loss, acc


# --- Main Execution ---
def main():
    print(f"Loading datasets on target: {DEVICE}...")
    datasets = load_datasets()
    x_val, y_val = build_validation_set(datasets)

    model = RecurrentSudokuTransformer().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    best_val_loss, patience_counter = float("inf"), 0

    for epoch in range(1, EPOCHS + 1):
        # Dynamically scale data window up without dropping previous rules
        active_x, active_y, highest_tier = get_curriculum_data(epoch, datasets)
        if epoch in [1, 4, 7, 10]:
            print(f">>> Curriculum Level Update: Highest tier is now '{highest_tier}'")

        loader = DataLoader(TensorDataset(active_x, active_y), batch_size=BS, shuffle=True)

        train_epoch(model, loader, optimizer, criterion)
        val_loss, acc = evaluate(model, x_val, y_val, criterion)

        print(f"Epoch {epoch:02d} | Pool: {len(active_x)} | Val Loss: {val_loss:.4f} | Global Acc: {acc:.2f}%")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), os.path.join(DATA_DIR, "sudoku_benchmark.pt"))
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"\n[Early Stopping] Triggered at epoch {epoch}")
                break


if __name__ == "__main__":
    main()