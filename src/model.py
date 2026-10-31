"""Model definitions.

``build_cnn``: the main model, a custom VGG-style CNN for 48x48 grayscale faces
(~0.71M parameters with the default filters (24, 48, 96, 192)):

    Input 48x48x1
    Block 1: [Conv f1 -> BN -> ReLU] x2 -> MaxPool -> Dropout 0.20   (24x24)
    Block 2: [Conv f2 -> BN -> ReLU] x2 -> MaxPool -> Dropout 0.25   (12x12)
    Block 3: [Conv f3 -> BN -> ReLU] x2 -> MaxPool -> Dropout 0.30   (6x6)
    Block 4: [Conv f4 -> BN -> ReLU] x2                               (6x6)  <- Grad-CAM layer
    GlobalAveragePooling -> Dense 256 -> BN -> ReLU -> Dropout 0.5
    Dense 7 -> Softmax

Two stacked 3x3 convolutions see a 5x5 region with fewer parameters than one
5x5 convolution. Global average pooling replaces a large Flatten->Dense layer,
which keeps the parameter count (and overfitting) low.
"""
from tensorflow import keras
from tensorflow.keras import layers

from src import config

GRADCAM_LAYER = "block4_2_relu"  # last convolutional feature map of build_cnn (6x6xf4)


def _conv_bn_relu(x, filters: int, name: str):
    x = layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_conv")(x)
    x = layers.BatchNormalization(name=f"{name}_bn")(x)
    return layers.ReLU(name=f"{name}_relu")(x)


def _block(x, filters: int, index: int, pool: bool, dropout: float):
    x = _conv_bn_relu(x, filters, f"block{index}_1")
    x = _conv_bn_relu(x, filters, f"block{index}_2")
    if pool:
        x = layers.MaxPooling2D(name=f"block{index}_pool")(x)
        x = layers.Dropout(dropout, name=f"block{index}_dropout")(x)
    return x


def build_cnn(learning_rate: float = config.LEARNING_RATE, filters=config.CNN_FILTERS) -> keras.Model:
    """Build and compile the baseline CNN."""
    inputs = keras.Input(shape=config.INPUT_SHAPE, name="face")
    f1, f2, f3, f4 = filters
    x = _block(inputs, f1, 1, pool=True, dropout=0.2)
    x = _block(x, f2, 2, pool=True, dropout=0.25)
    x = _block(x, f3, 3, pool=True, dropout=0.3)
    x = _block(x, f4, 4, pool=False, dropout=0.0)
    x = layers.GlobalAveragePooling2D(name="gap")(x)
    x = layers.Dense(256, use_bias=False, name="dense")(x)
    x = layers.BatchNormalization(name="dense_bn")(x)
    x = layers.ReLU(name="dense_relu")(x)
    x = layers.Dropout(0.5, name="dense_dropout")(x)
    outputs = layers.Dense(config.NUM_CLASSES, activation="softmax", name="predictions")(x)

    model = keras.Model(inputs, outputs, name="emotion_cnn")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate),
        loss="sparse_categorical_crossentropy",  # integer labels, no one-hot needed
        metrics=["accuracy"],
    )
    return model

