FROM freqtradeorg/freqtrade:stable

# Specify the working directory in the container
WORKDIR /freqtrade

# Copy the requirements file to the container
COPY strategy/requirements/requirements.txt /freqtrade/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /freqtrade/requirements.txt
# RUN pip install --no-cache-dir plotly==5.24.1