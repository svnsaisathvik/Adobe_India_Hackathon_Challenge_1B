# Intelligent Document Analyst - Challenge 1B

## How to Run

### 1. Build the Docker Image
Open a terminal in the project directory and run:

```
docker build -t adobe_challenge1b .
```


### 2. Run the Container
To process the input collections and generate the output JSONs:

#### On Windows:
```
docker run --rm -v "%cd%\input:/app/input" adobe_challenge1b
```

#### On Linux/macOS:
```
docker run --rm -v "$PWD/input:/app/input" adobe_challenge1b
```

- This command mounts your local `input` folder to `/app/input` inside the container.
- The output (`predicted_output.json`) will be written inside the corresponding collection folder in your local `input` directory.


## Changing the Input Location
- To change which collection is processed, edit the following line in `final_challenge1b_processor.py` (inside the `main()` function):
  ```python
  collection_dir = "input/Collection 2"
  ```
  Change `Collection 2` to your desired collection (e.g., `Collection 1`).

## Where to Find the Output
- The predicted output will be saved as `predicted_output.json` in the same collection directory as the input JSON (e.g., `input/Collection 2/predicted_output.json`).

## Approach
- The methodology and design choices are explained in detail in [approach_explanation.md](./approach_explanation.md).

---
For any further customization or questions, please refer to the code comments or the approach explanation file.
