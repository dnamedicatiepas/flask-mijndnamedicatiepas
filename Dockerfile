# Use an official Python runtime as a parent image
FROM python:3.10

LABEL maintainer="Mark Santcroos <m.a.santcroos@lumc.nl>"

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN pip install --progress-bar off --trusted-host pypi.python.org -r requirements_docker.txt

# Make port available to the world outside this container
EXPOSE 5000

# Define environment variables
ENV FLASK_APP app

CMD ["flask", "run", "--host", "0.0.0.0", "--debug"]
