.PHONY: all clean install build package

# Variables
VSCE := npx vsce
NPM := npm

# Default target
all: clean install build package

# Clean the project
clean:
	@echo "Cleaning..."
	rm -rf node_modules
	rm -rf dist
	rm -f *.vsix

# Install dependencies
install:
	@echo "Installing dependencies..."
	$(NPM) install

# Build the project
build:
	@echo "Building..."
	$(NPM) run compile

# Package the extension
package:
	@echo "Packaging..."
	$(VSCE) package

# Install and build
dev: clean install build

# Run tests
test:
	@echo "Running tests..."
	$(NPM) test

# Publish the extension (for maintainers only)
publish:
	@echo "Publishing..."
	$(VSCE) publish

# Help target
help:
	@echo "Available targets:"
	@echo "  all      : Clean, install dependencies, build, and package"
	@echo "  clean    : Remove build artifacts and dependencies"
	@echo "  install  : Install dependencies"
	@echo "  build    : Compile the extension"
	@echo "  package  : Create a .vsix package"
	@echo "  dev      : Clean, install, and build (for development)"
	@echo "  test     : Run tests"
	@echo "  publish  : Publish the extension (for maintainers only)"
	@echo "  help     : Show this help message"
