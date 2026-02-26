# AI Chatbot - Streamlit Web Application

A web-based AI chatbot interface for analyzing data from Newsense system using Google Gemini AI.

## Features

- 🔐 **User Authentication**: Login system with admin/user roles
- 💬 **Chatbot Interaction**: Interactive chat interface with AI-powered responses
- 📜 **Chat History**: View and search through all chat conversations
- 📊 **Knowledge Graph Editor**: Admin-only interface to edit knowledge graph (Excel file)
- 📈 **Data Visualization**: Automatic chart generation from Newsense data
- 🔍 **Data Analysis**: AI-powered analysis of fetched data

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

1. Edit `config.json` and fill in your credentials:

```json
{
  "api": {
    "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
    "base_url": "https://newsense.viphap.com/api",
    "tb_user": "YOUR_NEWSENSE_USERNAME",
    "tb_pass": "YOUR_NEWSENSE_PASSWORD"
  },
  "admin": {
    "username": "admin",
    "password": "admin123"
  },
  "knowledge_graph": {
    "path": "Knowledge_graph.xlsx"
  }
}
```

2. Make sure `Knowledge_graph.xlsx` exists in the project directory (or update the path in config.json)

## Running the Application

Start the Streamlit app:

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Usage

1. **Login**: Use the admin credentials from `config.json` to log in
2. **Chatbot Interaction**: 
   - Type your questions in natural language
   - The AI will analyze your query and fetch relevant data
   - View charts and analysis results
3. **Chat History**: Browse through all previous conversations
4. **Knowledge Graph Editor** (Admin only):
   - View and edit the knowledge graph
   - Upload new Excel files
   - Save changes

## Project Structure

```
.
├── app.py                 # Main Streamlit application
├── chatbot_core.py        # Core chatbot functionality
├── config.json            # Configuration file
├── requirements.txt       # Python dependencies
├── Knowledge_graph.xlsx   # Knowledge graph data
└── README.md             # This file
```

## Notes

- Default admin credentials: `admin` / `admin123` (change in config.json)
- The knowledge graph should be an Excel file with columns matching the expected format
- Make sure your Gemini API key and Newsense credentials are valid

