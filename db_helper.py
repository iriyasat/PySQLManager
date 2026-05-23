import base64
import hashlib
import json
import logging
import pymysql
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CredentialsCrypto:
    """
    Encrypts and decrypts database credentials to store them safely in the Flask session cookie.
    Key is derived from the app's secret key.
    """
    def __init__(self, secret_key: str):
        # Derive a stable 32-byte key from the Flask secret key using SHA-256
        key_hash = hashlib.sha256(secret_key.encode('utf-8')).digest()
        key_b64 = base64.urlsafe_b64encode(key_hash)
        self.fernet = Fernet(key_b64)

    def encrypt(self, data: dict) -> str:
        serialized = json.dumps(data).encode('utf-8')
        return self.fernet.encrypt(serialized).decode('utf-8')

    def decrypt(self, token: str) -> dict:
        try:
            decrypted = self.fernet.decrypt(token.encode('utf-8'))
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to decrypt credentials token: {e}")
            return {}

def get_db_connection(creds: dict, database: str = None):
    """
    Creates a new connection to the MySQL server based on user credentials.
    """
    # Use database specified in arguments, default to default database in credentials, or None.
    db_name = database if database is not None else creds.get('database')
    
    return pymysql.connect(
        host=creds.get('host', 'localhost'),
        port=int(creds.get('port', 3307)),
        user=creds.get('username', 'root'),
        password=creds.get('password', ''),
        database=db_name or None,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5
    )

def execute_query(creds: dict, query: str, params: tuple = None, database: str = None) -> dict:
    """
    Executes a single SQL query and returns result metrics and rows.
    """
    result = {
        'success': False,
        'columns': [],
        'rows': [],
        'affected_rows': 0,
        'last_row_id': 0,
        'warning_count': 0,
        'error': None,
        'query': query
    }
    
    conn = None
    try:
        conn = get_db_connection(creds, database=database)
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            
            # Fetch details
            result['affected_rows'] = cursor.rowcount
            result['last_row_id'] = cursor.lastrowid
            
            # If query returns rows (e.g. SELECT, SHOW, DESCRIBE)
            if cursor.description:
                result['columns'] = [desc[0] for desc in cursor.description]
                result['rows'] = list(cursor.fetchall())
                
            conn.commit()
            result['success'] = True
            
            # Check warnings
            warnings = cursor.execute("SHOW WARNINGS")
            if warnings > 0:
                result['warning_count'] = warnings
                
    except pymysql.MySQLError as e:
        if conn:
            conn.rollback()
        result['error'] = f"({e.args[0]}) {e.args[1]}" if len(e.args) > 1 else str(e)
        logger.error(f"MySQL Error: {result['error']} in query: {query}")
    except Exception as e:
        if conn:
            conn.rollback()
        result['error'] = str(e)
        logger.error(f"General Error: {e} in query: {query}")
    finally:
        if conn:
            conn.close()
            
    return result

def split_sql_script(sql_text: str) -> list:
    """
    Splits a SQL script into individual statements, ignoring comments and respecting semicolons inside strings.
    """
    statements = []
    current_statement = []
    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    
    chars = list(sql_text)
    length = len(chars)
    i = 0
    while i < length:
        c = chars[i]
        
        # Look ahead for comment patterns
        next_c = chars[i+1] if i + 1 < length else ''
        
        # Handle active line comment
        if in_line_comment:
            if c == '\n':
                in_line_comment = False
            i += 1
            continue
            
        # Handle active block comment
        if in_block_comment:
            if c == '*' and next_c == '/':
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
            
        # Check start of comment if not currently in string quotes
        if not (in_single_quote or in_double_quote or in_backtick):
            if c == '-' and next_c == '-':
                in_line_comment = True
                i += 2
                continue
            if c == '#':
                in_line_comment = True
                i += 1
                continue
            if c == '/' and next_c == '*':
                in_block_comment = True
                i += 2
                continue
                
        # Handle string and backtick boundaries (with escape sequence checking)
        if c == "'" and not (in_double_quote or in_backtick or (i > 0 and chars[i-1] == '\\')):
            in_single_quote = not in_single_quote
        elif c == '"' and not (in_single_quote or in_backtick or (i > 0 and chars[i-1] == '\\')):
            in_double_quote = not in_double_quote
        elif c == '`' and not (in_single_quote or in_double_quote or (i > 0 and chars[i-1] == '\\')):
            in_backtick = not in_backtick
            
        # Check statement delimiter
        if c == ';' and not (in_single_quote or in_double_quote or in_backtick):
            stmt = ''.join(current_statement).strip()
            if stmt:
                statements.append(stmt)
            current_statement = []
        else:
            current_statement.append(c)
            
        i += 1
        
    stmt = ''.join(current_statement).strip()
    if stmt:
        statements.append(stmt)
        
    return statements
