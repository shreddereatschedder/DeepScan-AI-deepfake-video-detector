# Development Diary - 09/10/2025
# TEMPLATE

---

## Task / Work Summary
Briefly describe what you worked on today/this week.

---

## Development Diary Table

### Date -- [xx/xx/xxxx]
Context/Problem/Challenge 
Begin sections with a brief "problem frame" — what is the issue, and why does it matter?

Approach/Method
Then, explain how you tackled it — what method, design, or thinking did you use?

Response/Solution
Finally, present the outcome or insight that followed.

---

## Code Snippets
Include any important code snippets relevant to the task.

```python
# Example: CNN model for leaf classification
model = tf.keras.models.Sequential([
    tf.keras.layers.Conv2D(32, (3,3), activation='relu', input_shape=(128,128,3)),
    tf.keras.layers.MaxPooling2D(2,2),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(num_classes, activation='softmax')
])
```
## Screenshots / Images
Embed images of your code, UI, graphs, or model outputs here.

## References / Resources
Tutorial / Article / Documentation URL
Research Paper / Dataset URL

## Next Steps / To-Do
[Task 1]
[Task 2]
[Task 3]
