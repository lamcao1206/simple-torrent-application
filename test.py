import time

for number in range(1, 101):
    print(f"\r{number}", end="", flush=True)  # Print the number in one line
    time.sleep(0.1)  # Adjust the delay as needed (0.5 seconds in this case)
