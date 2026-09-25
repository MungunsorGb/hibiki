# Labeled training data

Each subfolder is one class, and its name is used directly as the model's
label (see `ai/src/train_classifier.py`):

```
data/sample/
    Healthy/     *.csv
    Corrosion/   *.csv
    LooseBolt/   *.csv
```

Each `.csv` = one recorded tap: 3 columns, `X,Y,Z`, either with or without
a header row (auto-detected). This is the same format the ESP32 already
returns and that `ai/src/inspect_dataset.py` validates.

No sample data is committed here yet — these folders are placeholders so
the training script has somewhere real to look. Add your labeled taps,
then run:

```
python ai/src/train_classifier.py
```

which trains `ai/models/classifier.joblib` and prints an honest accuracy
readout only if there's enough data to hold out a real test split; with
too little data it says so instead of printing a misleading number.
