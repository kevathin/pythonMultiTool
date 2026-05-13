import json
import os
import tempfile
from sqliteTools import sqliteMultiTool


def main():
    try:
        print("Running test case 1...")
        test1()
        print("Finished test case 1.\n")
        print("Running test case 2...")
        test2()
        print("Finished test case 2.\n")
        print("Running test case 3...")
        test3()
        print("Finished test case 3.\n")
        print("All test cases completed.")
    except Exception as e:
        print(f"An error occurred: {e}")


def assert_equal(actual, expected, message=None):
    if actual != expected:
        raise AssertionError(message or f"Expected {expected!r}, got {actual!r}")


def test1():
    # Test case 1: test default db creation and delete_database behavior.
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        tool = sqliteMultiTool()
        expected_path = os.path.join(temp_dir, "example.db")
        actual_path = os.path.abspath(tool.get_path())
        assert_equal(os.path.realpath(actual_path), os.path.realpath(expected_path), "Default db_path should be example.db in current folder.")
        assert os.path.exists(expected_path), "example.db should be created by default constructor."

        deleted = tool.delete_database()
        assert_equal(deleted, True, "delete_database should return True.")
        assert tool.db_path is None, "db_path should be None after delete_database."
        assert not os.path.exists(expected_path), "Database file should be deleted."
    os.chdir(original_cwd)


def test2():
    # Test case 2: test db creation, path setting, and basic schema operations.
    with tempfile.TemporaryDirectory() as temp_dir:
        tool = sqliteMultiTool()

        created_db = tool.create_db(temp_dir, "test.db")
        assert_equal(os.path.basename(created_db), "test.db", "create_db should create the file with the given name.")
        assert os.path.exists(created_db), "Database file should exist after create_db."
        assert_equal(tool.get_path(), created_db, "get_path should return the created database path.")

        new_dir = os.path.join(temp_dir, "nested")
        os.makedirs(new_dir, exist_ok=True)
        set_path = tool.set_path(new_dir, "newtest.db")
        assert_equal(os.path.basename(set_path), "newtest.db", "set_path should append name if directory path is provided.")
        assert tool.get_path().endswith("newtest.db"), "db_path should be updated after set_path."

        assert tool.create_table("users", {"id": "INTEGER PRIMARY KEY", "username": "TEXT", "age": "INTEGER"}), "create_table should return True."
        assert "users" in tool.get_table_names(), "get_table_names should include the newly created table."
        assert_equal(tool.get_table_headers("users"), ["id", "username", "age"], "get_table_headers should return the correct column names.")

        assert tool.add_column("users", "email", "TEXT"), "add_column should return True."
        headers_after_add = tool.get_table_headers("users")
        assert "email" in headers_after_add, "Email column should be present after add_column."

        assert tool.add_row("users", {"username": "alice", "age": 30, "email": "alice@example.com"}), "add_row should accept dict input."
        assert tool.add_row("users", '{"username": "bob", "age": 25, "email": "bob@example.com"}'), "add_row should accept JSON string input."
        assert tool.add_row("users", ["username = 'carol'", "age = 27", "email = 'carol@example.com'"]), "add_row should accept list input."

        assert tool.update_row("users", 1, {"age": 31}), "update_row should accept dict input."
        assert tool.update_row("users", 2, '{"username": "robert"}'), "update_row should accept JSON string input."
        assert tool.update_row("users", 3, ["email = 'carol@newdomain.com'"]), "update_row should accept list input."

        query_result = json.loads(tool.run_query({"select": "username, age", "from": "users", "where": "age >= 25"}))
        assert_equal(query_result["success"], True, "run_query should execute successfully.")
        assert isinstance(query_result["results"], list), "run_query should return results as a list."

        assert tool.remove_row("users", 2), "remove_row should remove a row by id."
        try:
            tool.remove_row("users", 999)
            raise AssertionError("remove_row should raise a ValueError when no row is found.")
        except ValueError:
            pass

        assert tool.remove_column("users", "email"), "remove_column should return True."
        headers_after_remove = tool.get_table_headers("users")
        assert "email" not in headers_after_remove, "Email column should be removed."

        assert tool.delete_database(), "delete_database should return True after deletions."
        assert tool.db_path is None, "db_path should be None after delete_database."
        assert not os.path.exists(set_path), "Database file should no longer exist after delete_database."


def test3():
    # Test case 3: test query configuration helpers and construct_query.
    tool = sqliteMultiTool()
    query_dict = {"select": "id, username", "from": "users", "where": "age > 20", "order_by": "age DESC"}
    assert_equal(tool.construct_query(query_dict), "SELECT id, username FROM users WHERE age > 20 ORDER BY age DESC")

    json_query = '{"select": "id", "from": "users", "where": "age < 50"}'
    qualified = tool.configure_queryList(json_query)
    assert_equal(qualified["from"], "users")
    assert_equal(qualified["select"], "id")

    list_query = ["select id, username", "from users", "where age > 20", "order by age DESC"]
    qualified_list = tool.configure_queryList(list_query)
    assert_equal(qualified_list["order_by"], "age DESC")

    try:
        tool.configure_queryList(["invalid format"])
        raise AssertionError("configure_queryList should raise ValueError for invalid list format.")
    except ValueError:
        pass


if __name__ == "__main__":
    main()
