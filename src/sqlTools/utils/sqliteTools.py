import sqlite3
import json
import os


class sqliteMultiTool:
    def __init__(self, db_path=None):
        """
        Initialize the SQLite tool and ensure the database file exists.

        Cases:
            - No db_path: uses "example.db" in the current folder.
            - db_path points to an existing directory: creates "example.db" inside it.
            - db_path points to a file path that does not exist: creates that file.
        """
        if db_path is None:
            self.db_path = "example.db"
        elif not isinstance(db_path, str):
            raise ValueError("db_path must be a string or None.")
        elif os.path.isdir(db_path) or db_path.endswith(os.sep):
            self.db_path = os.path.join(db_path, "example.db")
        else:
            self.db_path = db_path

        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            conn.close()

    def _resolve_db_path(self, path, name=None):
        """
        Normalize a path so it includes a database file name.

        If the provided path already includes a file name, return it unchanged.
        Otherwise, append the provided name or use the current db_path file name.
        """
        if not isinstance(path, str):
            raise ValueError("Path must be a string.")
        if name is not None and not isinstance(name, str):
            raise ValueError("Name must be a string when provided.")

        normalized_path = path
        basename = os.path.basename(normalized_path)
        has_filename = bool(basename and not normalized_path.endswith(os.sep) and os.path.splitext(basename)[1])

        if not has_filename:
            if not name:
                current_name = os.path.basename(self.db_path) if isinstance(self.db_path, str) else ""
                if not current_name:
                    raise ValueError("A file name is required when the provided path does not already include one.")
                name = current_name
            normalized_path = os.path.join(normalized_path, name) if normalized_path else name

        return normalized_path

    def _standardize_update_data(self, update_data):
        """
        Standardizes the update_data input to a dictionary.

        Args:
            update_data: The input update data (dict, JSON string, or list of 'column = value' strings).
                Examples:
                - Dict: {"name": "John", "age": 30}
                - JSON: '{"name": "John", "age": 30}'
                - List: ["name = 'John'", "age = 30"]

        Returns:
            dict: A standardized dictionary of column: value pairs.

        Raises:
            ValueError: If the input cannot be converted.
        """
        def parse_update_list(lst):
            d = {}
            for item in lst:
                if not isinstance(item, str):
                    raise ValueError("List items must be strings in 'column = value' format.")
                if ' = ' not in item:
                    raise ValueError("List items must be in 'column = value' format.")
                key, value_str = item.split(' = ', 1)
                key = key.strip()
                value_str = value_str.strip()
                # Parse value: remove quotes if present, or convert numbers
                if (value_str.startswith("'") and value_str.endswith("'")) or (value_str.startswith('"') and value_str.endswith('"')):
                    value = value_str[1:-1]
                elif value_str.isdigit():
                    value = int(value_str)
                elif value_str.replace('.', '', 1).isdigit() and '.' in value_str:
                    value = float(value_str)
                else:
                    value = value_str  # keep as string
                d[key] = value
            return d

        try:
            if isinstance(update_data, dict):
                return update_data
            elif isinstance(update_data, str):
                return json.loads(update_data)
            elif isinstance(update_data, list):
                return parse_update_list(update_data)
            else:
                raise ValueError("update_data must be a dict, JSON string, or list of 'column = value' strings.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for update_data: {e}")
        except Exception as e:
            raise ValueError(f"Error standardizing update_data: {e}")

    def execute_query(self, query):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.commit()
            return results
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None
        finally:
            if conn:
                cursor.close()
                conn.close()

    def create_db(self, path, name):
        """
        Creates a new SQLite database file at the specified path with the given name.

        Args:
            path (str): The directory path (absolute or relative) or file path where the database will be created.
            name (str): The name of the database file (e.g., "mydb.db").

        Returns:
            str: The full path to the created database file.

        Raises:
            ValueError: If the path is invalid or database creation fails.
        """
        try:
            full_path = self._resolve_db_path(path, name)
            full_dir = os.path.dirname(full_path)

            if full_dir and not os.path.exists(full_dir):
                os.makedirs(full_dir, exist_ok=True)

            conn = sqlite3.connect(full_path)
            conn.close()

            self.db_path = full_path
            return full_path
        except Exception as e:
            raise ValueError(f"Error creating database: {e}")

    def get_path(self):
        """
        Returns the current database path.

        Returns:
            str: The current database file path.
        """
        return self.db_path

    def set_path(self, path, name=None):
        """
        Sets the database path to a new location.

        Args:
            path (str): The new database file path or directory path (absolute or relative).
            name (str, optional): The database file name if path does not already include one.

        Returns:
            str: The updated database path.
        """
        if not isinstance(path, str):
            raise ValueError("Path must be a string.")
        full_path = self._resolve_db_path(path, name)
        self.db_path = full_path
        return self.db_path

    def get_table_names(self):
        """
        Retrieves the names of all tables in the current database.

        Returns:
            list: A list of table names in the database. Empty list if no tables exist.

        Raises:
            ValueError: If the query fails.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Query to get all table names from sqlite_master
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            # Flatten the list of tuples to a list of strings
            return [table[0] for table in tables]
        except sqlite3.Error as e:
            raise ValueError(f"Error retrieving table names: {e}")

    def get_table_headers(self, table_name):
        """
        Retrieves the column headers (names) for a specific table in the database.

        Args:
            table_name (str): The name of the table.

        Returns:
            list: A list of column names for the specified table.

        Raises:
            ValueError: If the table doesn't exist or the query fails.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Query to get column information for the table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            conn.close()

            if not columns:
                raise ValueError(f"Table '{table_name}' does not exist or has no columns.")

            # Extract column names (second element in each tuple)
            return [column[1] for column in columns]
        except sqlite3.Error as e:
            raise ValueError(f"Error retrieving headers for table '{table_name}': {e}")

    def construct_query(self, queryList):
        """
        Constructs a SQL query string from a dictionary of query components.

        Args:
            queryList (dict): A dictionary containing SQL query components.
                - "select" (str, optional): The SELECT clause. Defaults to "*".
                - "from" (str, required): The FROM clause.
                - "join" (str, optional): The JOIN clause(s), e.g., "INNER JOIN table2 ON table1.id = table2.id".
                - "where" (str, optional): The WHERE clause.
                - "group_by" (str, optional): The GROUP BY clause.
                - "order_by" (str, optional): The ORDER BY clause.

        Returns:
            str: The constructed SQL query string.

        Raises:
            ValueError: If required clauses are missing or not formatted correctly.
        """
        try:
            # Extract and validate the SELECT clause
            select_clause = queryList.get("select", "*")
            if not isinstance(select_clause, str):
                raise ValueError("SELECT clause must be a string.")

            # Extract and validate the FROM clause (required)
            from_clause = queryList.get("from")
            if not from_clause or not isinstance(from_clause, str):
                raise ValueError("FROM clause is required and must be a string.")

            # Extract and validate the JOIN clause
            join_clause = queryList.get("join", "")
            if join_clause and not isinstance(join_clause, str):
                raise ValueError("JOIN clause must be a string.")

            # Extract and validate the WHERE clause
            where_clause = queryList.get("where", "")
            if where_clause and not isinstance(where_clause, str):
                raise ValueError("WHERE clause must be a string.")

            # Extract and validate the GROUP BY clause
            group_by_clause = queryList.get("group_by", "")
            if group_by_clause and not isinstance(group_by_clause, str):
                raise ValueError("GROUP BY clause must be a string.")

            # Extract and validate the ORDER BY clause
            order_by_clause = queryList.get("order_by", "")
            if order_by_clause and not isinstance(order_by_clause, str):
                raise ValueError("ORDER BY clause must be a string.")

            # Build the SQL query string
            query = f"SELECT {select_clause} FROM {from_clause}"
            if join_clause:
                query += f" {join_clause}"
            if where_clause:
                query += f" WHERE {where_clause}"
            if group_by_clause:
                query += f" GROUP BY {group_by_clause}"
            if order_by_clause:
                query += f" ORDER BY {order_by_clause}"

            return query
        except KeyError as e:
            raise ValueError(f"Missing required key in queryList: {e}")
        except Exception as e:
            raise ValueError(f"Error constructing query: {e}")

    def configure_queryList(self, queryList):
        """
        Configures and normalizes the queryList input for use with construct_query.

        Supports inputs as dict, JSON string, or list of clause strings.
        Validates that the resulting dict has recognized keys and string values, with 'from' required.

        Args:
            queryList: The input query list (dict, JSON string, or list of strings).

        Returns:
            dict: A normalized and validated dictionary suitable for construct_query.

        Raises:
            ValueError: If the input cannot be converted or is not correctly structured.
        """
        def validate_query_dict(d):
            expected_keys = {"select", "from", "join", "where", "group_by", "order_by"}
            for key in d:
                if key not in expected_keys:
                    raise ValueError(f"Unrecognized key '{key}' in queryList.")
                if not isinstance(d[key], str):
                    raise ValueError(f"Value for '{key}' must be a string.")
            if "from" not in d or not d["from"]:
                raise ValueError("FROM clause is required.")

        def parse_list_to_dict(lst):
            d = {}
            for item in lst:
                if not isinstance(item, str):
                    raise ValueError("List items must be strings.")
                parts = item.strip().split(None, 1)
                if len(parts) < 1:
                    continue
                keyword = parts[0].lower()
                value = parts[1] if len(parts) > 1 else ""
                if keyword == "select":
                    d["select"] = value
                elif keyword == "from":
                    d["from"] = value
                elif keyword == "join":
                    d["join"] = item  # Keep full clause
                elif keyword == "where":
                    d["where"] = value
                elif keyword == "group":
                    if len(parts) > 2 and parts[1].lower() == "by":
                        d["group_by"] = " ".join(parts[2:])
                    else:
                        raise ValueError("Invalid GROUP BY clause.")
                elif keyword == "order":
                    if len(parts) > 2 and parts[1].lower() == "by":
                        d["order_by"] = " ".join(parts[2:])
                    else:
                        raise ValueError("Invalid ORDER BY clause.")
                else:
                    raise ValueError(f"Unrecognized clause '{keyword}'.")
            return d

        try:
            if isinstance(queryList, dict):
                d = queryList
            elif isinstance(queryList, str):
                d = json.loads(queryList)
            elif isinstance(queryList, list):
                d = parse_list_to_dict(queryList)
            else:
                raise ValueError("queryList must be a dict, JSON string, or list of strings.")
            
            validate_query_dict(d)
            return d
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string provided: {e}")
        except Exception as e:
            raise ValueError(f"Error configuring queryList: {e}")

    def run_query(self, queryList):
        """
        Executes a complete query workflow: configure, construct, and execute.

        Args:
            queryList: The input query list (dict, JSON string, or list of strings).

        Returns:
            str: A JSON string containing the query results.
                Format: {"success": true, "query": "...", "results": [...]}
                On error: {"success": false, "error": "..."}

        Raises:
            ValueError: If configuration, construction, or execution fails.
        """
        try:
            # Step 1: Configure and normalize the queryList
            configured_dict = self.configure_queryList(queryList)

            # Step 2: Construct the SQL query
            sql_query = self.construct_query(configured_dict)

            # Step 3: Execute the query
            results = self.execute_query(sql_query)

            # Step 4: Return as JSON
            if results is None:
                return json.dumps({
                    "success": False,
                    "error": "Query execution failed. Check database connection."
                })

            return json.dumps({
                "success": True,
                "query": sql_query,
                "results": results
            })
        except ValueError as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Unexpected error during query execution: {str(e)}"
            })

    def create_table(self, table_name, columns=None):
        """
        Creates a new table in the database.

        Args:
            table_name (str): The name of the table to create.
            columns (dict, optional): A dictionary where keys are column names and values are column types.
                Example: {"id": "INTEGER PRIMARY KEY", "name": "TEXT", "age": "INTEGER"}
                If None, creates a table with a default 'id' column as PRIMARY KEY.

        Returns:
            bool: True if table was created successfully, False otherwise.

        Raises:
            ValueError: If table creation fails.
        """
        try:
            if not table_name:
                raise ValueError("Table name cannot be empty.")

            # Use default columns if none provided
            if columns is None:
                columns = {"id": "INTEGER PRIMARY KEY"}
            
            if not isinstance(columns, dict):
                raise ValueError("Columns must be a dictionary.")

            # Build column definitions
            column_defs = ", ".join([f"{col_name} {col_type}" for col_name, col_type in columns.items()])
            
            # Create table query
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_defs});"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            conn.close()
            
            return True
        except sqlite3.Error as e:
            raise ValueError(f"Error creating table '{table_name}': {e}")

    def add_column(self, table_name, column_name, column_type):
        """
        Adds a new column to an existing table.

        Args:
            table_name (str): The name of the table.
            column_name (str): The name of the new column.
            column_type (str): The data type of the column (e.g., "TEXT", "INTEGER").

        Returns:
            bool: True if column was added successfully.

        Raises:
            ValueError: If the operation fails.
        """
        try:
            if not table_name or not column_name or not column_type:
                raise ValueError("Table name, column name, and column type cannot be empty.")

            query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            conn.close()
            
            return True
        except sqlite3.Error as e:
            raise ValueError(f"Error adding column '{column_name}' to table '{table_name}': {e}")

    def remove_column(self, table_name, column_name):
        """
        Removes a column from a table.

        Note: SQLite has limited ALTER TABLE support. This method creates a new table
        without the column, copies data, drops the old table, and renames the new one.

        Args:
            table_name (str): The name of the table.
            column_name (str): The name of the column to remove.

        Returns:
            bool: True if column was removed successfully.

        Raises:
            ValueError: If the operation fails.
        """
        try:
            if not table_name or not column_name:
                raise ValueError("Table name and column name cannot be empty.")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()
            
            # Get all column names except the one to remove
            columns = [col[1] for col in columns_info if col[1] != column_name]
            
            if len(columns) == len(columns_info):
                raise ValueError(f"Column '{column_name}' not found in table '{table_name}'.")

            if not columns:
                raise ValueError("Cannot remove all columns from a table.")

            # Get original table schema
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            original_schema = cursor.fetchone()[0]

            # Create temporary table with remaining columns
            temp_table = f"{table_name}_temp"
            columns_str = ", ".join(columns)
            cursor.execute(f"CREATE TABLE {temp_table} AS SELECT {columns_str} FROM {table_name};")

            # Drop original table
            cursor.execute(f"DROP TABLE {table_name};")

            # Rename temporary table to original name
            cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name};")

            conn.commit()
            conn.close()

            return True
        except sqlite3.Error as e:
            raise ValueError(f"Error removing column '{column_name}' from table '{table_name}': {e}")

    def add_row(self, table_name, row_data):
        """
        Adds a row of data to a table.

        Args:
            table_name (str): The name of the table.
            row_data (dict): A dictionary where keys are column names and values are the data.
                Example: {"name": "John", "age": 30}

        Returns:
            bool: True if row was added successfully.

        Raises:
            ValueError: If the operation fails.
        """
        try:
            if not table_name or not isinstance(row_data, dict):
                raise ValueError("Table name must be provided and row_data must be a dictionary.")

            if not row_data:
                raise ValueError("row_data cannot be empty.")

            # Build INSERT query
            columns = ", ".join(row_data.keys())
            placeholders = ", ".join(["?" for _ in row_data.values()])
            values = list(row_data.values())

            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            conn.close()

            return True
        except sqlite3.Error as e:
            raise ValueError(f"Error adding row to table '{table_name}': {e}")

    def remove_row(self, table_name, id_value, id_column='id'):
        """
        Removes a row from a table by the specified ID column.

        Args:
            table_name (str): The name of the table.
            id_value: The value of the ID to delete.
            id_column (str, optional): The name of the ID column. Defaults to 'id'.

        Returns:
            bool: True if row was removed successfully.

        Raises:
            ValueError: If the operation fails.
        """
        try:
            if not table_name or id_value is None or not id_column:
                raise ValueError("Table name, id_value, and id_column cannot be empty.")

            query = f"DELETE FROM {table_name} WHERE {id_column} = ?;"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, (id_value,))
            conn.commit()
            
            # Check if row was actually deleted
            rows_deleted = cursor.rowcount
            conn.close()

            if rows_deleted == 0:
                raise ValueError(f"No row found with {id_column} = {id_value} in table '{table_name}'.")

            return True
        except sqlite3.Error as e:
            raise ValueError(f"Error removing row from table '{table_name}': {e}")

    def update_row(self, table_name, id_value, update_data, id_column='id'):
        """
        Updates a row in a table by the specified ID column.

        Args:
            table_name (str): The name of the table.
            id_value: The value of the ID to update.
            update_data: The data to update (dict, JSON string, or list of 'column = value' strings).
                Examples:
                - Dict: {"name": "Jane", "age": 31}
                - JSON: '{"name": "Jane", "age": 31}'
                - List: ["name = 'Jane'", "age = 31"]
            id_column (str, optional): The name of the ID column. Defaults to 'id'.

        Returns:
            bool: True if row was updated successfully.

        Raises:
            ValueError: If the operation fails.
        """
        try:
            if not table_name or id_value is None or not id_column:
                raise ValueError("Table name, id_value, and id_column cannot be empty.")

            # Standardize update_data
            standardized_data = self._standardize_update_data(update_data)

            if not standardized_data:
                raise ValueError("update_data cannot be empty.")

            # Build UPDATE query
            set_clause = ", ".join([f"{col} = ?" for col in standardized_data.keys()])
            values = list(standardized_data.values()) + [id_value]

            query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = ?;"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            
            # Check if row was actually updated
            rows_updated = cursor.rowcount
            conn.close()

            if rows_updated == 0:
                raise ValueError(f"No row found with {id_column} = {id_value} in table '{table_name}'.")

            return True
        except sqlite3.Error as e:
            raise ValueError(f"Error updating row in table '{table_name}': {e}")



        