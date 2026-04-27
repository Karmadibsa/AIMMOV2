import os
import torch
import torch.nn as nn
from torchvision import models, transforms, datasets
from torch.utils.data import DataLoader
from PIL import Image

# =========================
# CONFIG
# =========================
DATA_DIR = "data/photos"
MODEL_PATH = "model.pth"
IMG_SIZE = 224
BATCH_SIZE = 16
EPOCHS = 10
LR = 1e-4

CLASSES = ["excellent", "bon", "correct", "a_renover"]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =========================
# MODEL
# =========================
def build_model(num_classes=4):
    model = models.resnet18(pretrained=True)
    
    # Freeze partiel (optionnel mais utile petit dataset)
    for param in model.parameters():
        param.requires_grad = False

    # On entraîne seulement la dernière couche
    model.fc = nn.Linear(model.fc.in_features, num_classes)

    return model.to(DEVICE)

# =========================
# DATA
# =========================
def get_dataloaders(data_dir):
    train_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ToTensor(),
    ])

    dataset = datasets.ImageFolder(data_dir, transform=train_transforms)

    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    return dataloader, dataset.classes

# =========================
# TRAIN
# =========================
def train():
    dataloader, classes = get_dataloaders(DATA_DIR)

    model = build_model(len(classes))

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.fc.parameters(), lr=LR)

    print(f"Training on {DEVICE}")
    print(f"Classes: {classes}")

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0

        for images, labels in dataloader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()

            outputs = model(images)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            running_loss += loss.item()

        print(f"Epoch {epoch+1}/{EPOCHS} - Loss: {running_loss:.4f}")

    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

# =========================
# PREDICT
# =========================
def load_model():
    model = build_model(len(CLASSES))
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()
    return model

def predict(image_path):
    model = load_model()

    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
    ])

    image = Image.open(image_path).convert("RGB")
    image = transform(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = model(image)
        probs = torch.softmax(outputs, dim=1)[0]

    result = {CLASSES[i]: float(probs[i]) for i in range(len(CLASSES))}
    predicted_class = CLASSES[probs.argmax().item()]

    return {
        "prediction": predicted_class,
        "probabilities": result
    }

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    train()

    # Exemple test
    # print(predict("test.jpg"))