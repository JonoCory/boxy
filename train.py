import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

# 1. Load Data
df = pd.read_csv('gesture_dataset.csv')
X = df.iloc[:, 1:].values
y_text = df.iloc[:, 0].values

encoder = LabelEncoder()
y = encoder.fit_transform(y_text)
with open('label_encoder.pkl', 'wb') as f:
    pickle.dump(encoder, f)

# 2. Split Data (Train vs Validation)
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

X_train, X_val = torch.FloatTensor(X_train), torch.FloatTensor(X_val)
y_train, y_val = torch.LongTensor(y_train), torch.LongTensor(y_val)

# 3. Model Architecture
class GestureBrain(nn.Module):
    def __init__(self, num_classes):
        super(GestureBrain, self).__init__()
        # Added Dropout to prevent overfitting (Good for your report!)
        self.net = nn.Sequential(
            nn.Linear(63, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.net(x)

model = GestureBrain(len(encoder.classes_))
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 4. Training Loop with Validation
epochs = 150
for epoch in range(epochs):
    model.train()
    optimizer.zero_grad()
    outputs = model(X_train)
    loss = criterion(outputs, y_train)
    loss.backward()
    optimizer.step()
    
    # Validation step
    if (epoch+1) % 30 == 0:
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val)
            val_loss = criterion(val_outputs, y_val)
            _, predicted = torch.max(val_outputs.data, 1)
            acc = (predicted == y_val).sum().item() / len(y_val) * 100
        print(f'Epoch {epoch+1:03d} | Train Loss: {loss.item():.4f} | Val Loss: {val_loss.item():.4f} | Val Acc: {acc:.2f}%')

torch.save(model.state_dict(), 'gesture_model.pth')
print("Model and Encoder saved successfully.")