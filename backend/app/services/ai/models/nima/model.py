"""
NIMA (Neural Image Assessment) model architecture
Based on: https://arxiv.org/abs/1709.05424
"""
import torch
import torch.nn as nn
from torchvision import models


class NIMA(nn.Module):
    """
    Neural Image Assessment model.
    Uses a pretrained backbone (default: MobileNetV2) with a custom head
    for aesthetic quality classification.
    """

    def __init__(self, num_classes: int = 10, backbone: str = "mobilenetv2") -> None:
        """
        Initialize NIMA model.

        Args:
            num_classes: Number of output classes (default: 10 for 1-10 scoring)
            backbone: Backbone architecture to use
        """
        super().__init__()
        self.num_classes = num_classes

        # Create backbone
        self.backbone = backbone

        if backbone == "mobilenetv2":
            base_model = models.mobilenet_v2(weights=None)
            features = base_model.features
            in_features = base_model.last_channel
        elif backbone == "squeeze":
            base_model = models.squeezenet1_1(weights=None)
            features = base_model.features
            # This project ships weights trained with flattened SqueezeNet features.
            # Output shape before classifier is 512 x 13 x 13 => 86528.
            in_features = 86528
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")

        self.features = features

        # Custom classification head
        self.classifier = nn.Sequential(
            nn.Dropout(p=0.75 if backbone == "squeeze" else 0.2),
            nn.Linear(in_features, num_classes),
            nn.Softmax(dim=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (batch_size, 3, 224, 224)

        Returns:
            Probability distribution over aesthetic scores
        """
        features = self.features(x)
        if features.dim() == 4:
            if self.backbone == "squeeze":
                features = features.view(features.size(0), -1)
            else:
                # Global average pooling for backbones expecting pooled features.
                features = features.mean([2, 3])

        output = self.classifier(features)
        return output

    def predict_score(self, x: torch.Tensor) -> torch.Tensor:
        """
        Predict mean aesthetic score.

        Args:
            x: Input tensor

        Returns:
            Mean predicted score
        """
        probs = self.forward(x)
        # Calculate expected value: sum(p_i * i) where i goes from 1 to num_classes
        weights = torch.arange(1, self.num_classes + 1, dtype=torch.float32, device=x.device)
        mean_score = (probs * weights).sum(dim=1)
        return mean_score
