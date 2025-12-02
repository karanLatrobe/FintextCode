import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, DataCollatorForSeq2Seq, TrainingArguments, Trainer

# -----------------------
# 1. Select small model (BEST OPTION)
# -----------------------
model_name = "google/flan-t5-base"

# -----------------------
# 2. Load your dataset
# -----------------------
dataset = load_dataset("json", data_files="dataset.jsonl", split="train")

# -----------------------
# 3. Preprocessing for training
# -----------------------
def preprocess(example):
    instruction = (
        "Classify the bank transaction into the correct category.\n"
        "Return ONLY the category name.\n\n"
        f"Transaction: {example['input']}\n"
        "Category:"
    )
    return {
        "input_text": instruction,
        "target_text": example["output"]
    }

dataset = dataset.map(preprocess)

# -----------------------
# 4. Load tokenizer & model
# -----------------------
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def tokenize(batch):
    inputs = tokenizer(batch["input_text"], padding="max_length", truncation=True, max_length=256)
    labels = tokenizer(batch["target_text"], padding="max_length", truncation=True, max_length=10)
    inputs["labels"] = labels["input_ids"]
    return inputs

tokenized = dataset.map(tokenize, batched=True)

# -----------------------
# 5. Training setup
# -----------------------
args = TrainingArguments(
    output_dir="fintext-small-model",
    per_device_train_batch_size=2,
    num_train_epochs=3,
    learning_rate=3e-5,
    logging_steps=10,
    save_total_limit=1,
)

data_collator = DataCollatorForSeq2Seq(tokenizer)

# -----------------------
# 6. Trainer
# -----------------------
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized,
    data_collator=data_collator
)

trainer.train()

# -----------------------
# 7. Save trained model
# -----------------------
trainer.save_model("fintext-small-model")
tokenizer.save_pretrained("fintext-small-model")

print("Training Completed Successfully!")
