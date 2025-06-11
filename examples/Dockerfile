# Use the official Python base image
FROM python:3.13-slim

# Install bash
RUN apt-get update && apt-get install -y bash git vim npm

# Installs requirements
RUN pip install --upgrade pip && pip install --upgrade git+https://github.com/Mieschendahl/JSGenerator.git

# Create a new user and group
RUN useradd -m user

# Switch to the new user
USER user

# Set work dir
WORKDIR /home/user/jsgenerator/examples

# Copy files
COPY --chown=user:user ./examples/example_* ./

# Start an interactive bash shell by default
CMD ["bash"]