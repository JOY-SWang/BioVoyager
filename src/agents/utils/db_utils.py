import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "agent",
    "password": "88888888",
    "database": "chembl35DB",
    "unix_socket": "/var/run/mysqld/mysqld.sock"
}

def execute_query(sql, params=None):
    """
    Execute a generic SQL query against the configured MySQL database.
    :param sql: SQL query string with placeholders.
    :param params: Tuple or list of parameters to bind to the query.
    :return: List of rows (tuples) returned by the query.
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute(sql, params or ())
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results
