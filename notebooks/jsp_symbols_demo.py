#!/usr/bin/env python
# coding: utf-8

"""
JSP Symbol Extraction Demo

This script demonstrates how to use the jsp_get_all_file_symbols function 
from IndexManager to extract symbols from JSP files.

The demo includes:
- Setting up mock JSP files
- Initializing LLM model
- Creating an IndexManager instance
- Extracting symbols from JSP files
- Displaying the results
"""

import os
import sys
import tempfile
import time
from typing import Dict
from pathlib import Path

import byzerllm
from loguru import logger
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.index.index import IndexManager

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("jsp_symbols_demo.log", rotation="100 MB", level="DEBUG")

def setup_mock_jsp_files(temp_dir: str) -> Dict[str, str]:
    """Create mock JSP files for testing"""
    # Create sample JSP files
    jsp_files = {
        "index.jsp": """
<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>JSP Demo Page</title>
    <script language="javascript" src="/js/common.js"></script>
    <script language="javascript" src="/js/validation.js"></script>
</head>
<body>
    <jsp:include page="/jspf/header.jspf" />
    
    <%!
        // Class declaration
        class User {
            private String username;
            private int age;
            
            public User(String username, int age) {
                this.username = username;
                this.age = age;
            }
            
            public String getUsername() {
                return username;
            }
        }
        
        // Function declarations
        public String formatDate(java.util.Date date) {
            return new java.text.SimpleDateFormat("yyyy-MM-dd").format(date);
        }
        
        public int calculateAge(java.util.Date birthDate) {
            // Calculate age based on birth date
            return 30; // Simplified for demo
        }
    %>
    
    <%
        // Variables
        String pageTitle = "User Dashboard";
        int userCount = 10;
        boolean isAdmin = false;
        
        // Create a user object
        User currentUser = new User("john_doe", 28);
    %>
    
    <div class="container">
        <h1><%= pageTitle %></h1>
        
        <form name="userForm" action="/user/update.do" method="post">
            <input type="text" name="username" value="<%= currentUser.getUsername() %>" />
            <input type="submit" value="Update" />
        </form>
        
        <jsp:include page="/jspf/footer.jspf" />
    </div>
</body>
</html>
""",
        "login.jsp": """
<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Login Page</title>
    <script language="javascript" src="/js/login.js"></script>
</head>
<body>
    <jsp:include page="/jspf/header.jspf" />
    
    <%!
        // Function to validate credentials
        private boolean validateCredentials(String username, String password) {
            // In a real application, this would check against a database
            return "admin".equals(username) && "password123".equals(password);
        }
        
        // Function to encode password
        private String encodePassword(String password) {
            // Simple encoding for demonstration
            return password + "_encoded";
        }
    %>
    
    <%
        // Variables
        String errorMessage = "";
        boolean showError = false;
        
        // Check if form was submitted
        if ("POST".equals(request.getMethod())) {
            String username = request.getParameter("username");
            String password = request.getParameter("password");
            
            if (validateCredentials(username, password)) {
                session.setAttribute("user", username);
                response.sendRedirect("index.jsp");
            } else {
                errorMessage = "Invalid username or password";
                showError = true;
            }
        }
    %>
    
    <div class="login-container">
        <h2>Login</h2>
        
        <% if (showError) { %>
            <div class="error"><%= errorMessage %></div>
        <% } %>
        
        <form name="loginForm" action="login.jsp" method="post">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required />
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required />
            </div>
            <button type="submit">Login</button>
        </form>
    </div>
    
    <jsp:include page="/jspf/footer.jspf" />
</body>
</html>
"""
    }

    # Create files
    for filepath, content in jsp_files.items():
        full_path = os.path.join(temp_dir, filepath)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    logger.info(f"Created {len(jsp_files)} mock JSP files in {temp_dir}")
    return jsp_files

def get_llm_instance(model_name: str = "v3_chat", use_pro_mode: bool = False):
    """Initialize LLM instance similar to long_context_rag_demo.py"""
    logger.info(f"Initializing LLM (mode: {'pro' if use_pro_mode else 'lite'}, model: {model_name})")
    
    if use_pro_mode:
        # Pro mode: Use Ray cluster
        logger.info("Initializing Pro mode LLM...")
        byzerllm.connect_cluster()
        llm = byzerllm.ByzerLLM()
        llm.skip_nontext_check = True
        llm.setup_default_model_name(model_name)
    else:
        # Lite mode: Use cloud API
        logger.info("Initializing Lite mode LLM...")
        from autocoder import models as models_module
        model_info = models_module.get_model_by_name(model_name)
        llm = byzerllm.SimpleByzerLLM(default_model_name=model_name)
        llm.deploy(
            model_path="",
            pretrained_model_type=model_info["model_type"],
            udf_name=model_name,
            infer_params={
                "saas.base_url": model_info["base_url"],
                "saas.api_key": model_info["api_key"],
                "saas.model": model_info["model_name"],
                "saas.is_reasoning": model_info["is_reasoning"]
            }
        )
    
    return llm

def extract_jsp_symbols(llm, source_dir: str, jsp_files: Dict[str, str]):
    """Extract symbols from JSP files using IndexManager"""
    # Create AutoCoderArgs
    args = AutoCoderArgs(
        source_dir=source_dir,
        product_mode="lite",
        index_model_anti_quota_limit=1,
        anti_quota_limit=1
    )
    
    # Create SourceCode objects for each JSP file
    sources = []
    for filename, content in jsp_files.items():
        file_path = os.path.join(source_dir, filename)
        sources.append(SourceCode(module_name=file_path, source_code=content))
    
    # Create IndexManager instance
    index_manager = IndexManager(llm=llm, sources=sources, args=args)
    
    # Extract symbols from each JSP file
    results = {}
    for filepath, content in jsp_files.items():
        full_path = os.path.join(source_dir, filepath)
        logger.info(f"Extracting symbols from {filepath}...")
        
        # Use the jsp_get_all_file_symbols method to extract symbols
        try:
            symbols = index_manager.jsp_get_all_file_symbols.with_llm(index_manager.llm).run(full_path, content)
            results[filepath] = symbols
            logger.info(f"Successfully extracted symbols from {filepath}")
        except Exception as e:
            logger.error(f"Error extracting symbols from {filepath}: {str(e)}")
    
    return results

def display_results(results: Dict[str, str]):
    """Display extracted symbols from JSP files"""
    print("\n" + "="*80)
    print("JSP SYMBOL EXTRACTION RESULTS")
    print("="*80)
    
    for filepath, symbols in results.items():
        print(f"\nFile: {filepath}")
        print("-"*50)
        if symbols:
            print(symbols)
        else:
            print("No symbols extracted")
    
    print("\n" + "="*80)

def run_jsp_symbols_demo():
    """Run the JSP symbols extraction demo"""
    # Create temporary directory for mock files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup mock JSP files
        jsp_files = setup_mock_jsp_files(temp_dir)
        
        # Choose mode and model
        use_pro_mode = False  # Default to Lite mode
        if len(sys.argv) > 1 and sys.argv[1].lower() == "pro":
            use_pro_mode = True
        
        model_name = "v3_chat"  # Default model
        if len(sys.argv) > 2:
            model_name = sys.argv[2]
        
        try:
            # Initialize LLM
            llm = get_llm_instance(model_name, use_pro_mode)
            
            # Extract symbols from JSP files
            logger.info("Starting JSP symbol extraction...")
            start_time = time.time()
            results = extract_jsp_symbols(llm, temp_dir, jsp_files)
            extraction_time = time.time() - start_time
            
            # Display results
            display_results(results)
            
            # Log summary
            logger.info(f"Symbol extraction completed in {extraction_time:.2f} seconds")
            logger.info(f"Processed {len(jsp_files)} JSP files")
            
            return True
        
        except Exception as e:
            logger.error(f"Error in JSP symbols demo: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    logger.info("=== Starting JSP Symbol Extraction Demo ===")
    success = run_jsp_symbols_demo()
    if success:
        logger.info("=== Demo completed successfully ===")
    else:
        logger.error("=== Demo failed ===") 