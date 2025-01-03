# Use an official NGINX runtime as the base image
FROM ${ECR_REPOSITORY_URI}/${IMAGE_NAME}:${IMAGE_DEFAULT_TAG}

# Set the working directory to the NGINX web root
WORKDIR /usr/share/nginx/html

# Copy the default index.html file to the working directory
COPY index.html .

# Create version.html file with Nginx version information
RUN echo "Nginx version: $(nginx -v 2>&1 | awk -F / '{print $2}')" > version.html

# Expose port 80 for incoming traffic
EXPOSE 80

# Start the NGINX web server when the container starts
CMD ["nginx", "-g", "daemon off;"]
