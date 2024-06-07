import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import time

from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}
app.config['VECTORS'] = None
app.config['PDF_FILENAMES'] = []

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

groq_api_key = os.getenv("GROQ_API_KEY")
os.environ['GOOGLE_API_KEY'] = os.getenv("GOOGLE_API_KEY")

llm = ChatGroq(groq_api_key=groq_api_key, model_name="Gemma-7b-it")

prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate response based on the question.
    <context>
    {context}
    <context>
    Questions:{input}
    """
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def vector_embedding(directory):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    loader = PyPDFDirectoryLoader(directory)
    pages = loader.load_and_split()
    vectors = FAISS.from_documents(pages, embeddings)
    return vectors

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files part"}), 400

    uploaded_files = request.files.getlist('files')
    uploaded_filenames = []

    for file in uploaded_files:
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_filenames.append(filename)
            app.config['PDF_FILENAMES'].append(filename)
        else:
            return jsonify({"error": "File type not allowed"}), 400

    # Perform vector embedding after all files are uploaded
    app.config['VECTORS'] = vector_embedding(app.config['UPLOAD_FOLDER'])

    return jsonify({"message": "Files uploaded and vector store ready", "uploaded_files": uploaded_filenames}), 200

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question')
    if not question:
        return jsonify({"error": "No question provided"}), 400

    if not app.config['VECTORS']:
        return jsonify({"error": "No vectors available. Upload a PDF first."}), 400

    document_chain = create_stuff_documents_chain(llm, prompt)
    retriever = app.config['VECTORS'].as_retriever()
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    start = time.process_time()
    response = retrieval_chain.invoke({'input': question})
    response_time = time.process_time() - start

    return jsonify({
        "answer": response['answer'],
        "response_time": response_time,
        "context": [{"source": doc.metadata["source"][8:], "page": int(doc.metadata["page"])+1} for doc in response["context"]]
    })

@app.route('/get-pdf/<path:pdf_name>', methods=['GET'])
def get_pdf(pdf_name):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_name)
    if os.path.exists(pdf_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_name)
    else:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/get-pdf-names', methods=['GET'])
def get_pdf_names():
    return jsonify({"pdfNames": app.config['PDF_FILENAMES']}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
