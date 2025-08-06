import os
import psycopg2
from decimal import Decimal

class DatabaseHandler:
    def __init__(self):
        self.db_name = os.getenv("POSTGRES_NAME", "")
        self.db_user = os.getenv("POSTGRES_USER", "")
        self.db_password = os.getenv("POSTGRES_PASSWORD", "")
        self.db_host = os.getenv("POSTGRES_HOST", "")
        self.db_port = os.getenv("DB_PORT", "")
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port
            )
            print("Database connection successful!")
        except psycopg2.OperationalError as e:
            print(f"Could not connect to the database: {e}")
            raise

    def disconnect(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    def process_scraped_data(self, products_to_process):
        if not self.conn:
            print("Cannot process data, no database connection.")
            return
            
        if not products_to_process:
            print("No products to process. Exiting.")
            return
        
        cursor = self.conn.cursor()
        try:
            print("Setting all products to inactive...")
            cursor.execute("UPDATE deal_board_product SET is_active = FALSE;")

            for product in products_to_process:
                cursor.execute(
                    "SELECT id, latest_price FROM deal_board_product WHERE source_url = %s;",
                    (product["source_url"],)
                )
                result = cursor.fetchone()

                product_id = None
                if result:
                    product_id, old_price = result
                    print(f"Updating product: {product['name'][:30]}...")
                    cursor.execute(
                        """
                        UPDATE deal_board_product
                        SET latest_price = %s, discount_percentage = %s, is_active = TRUE, updated_at = NOW()
                        WHERE id = %s;
                        """,
                        (product["price"], product["discount"], product_id)
                    )
                # if result was None, it's a new product we've never seen before
                else:
                    print(f"Inserting new product: {product['name'][:30]}...")
                    cursor.execute(
                        """
                        INSERT INTO deal_board_product (name, source_url, image_url, latest_price, discount_percentage, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW()) RETURNING id;
                        """,
                        (product["name"], product["source_url"], product["image_url"], product["price"], product["discount"])
                    )
                    product_id_result = cursor.fetchone()
                    if product_id_result:
                        product_id = product_id_result[0]

                if product_id:
                    cursor.execute(
                        """
                        INSERT INTO deal_board_pricelog (product_id, price, scraped_at)
                        VALUES (%s, %s, NOW());
                        """,
                        (product_id, product["price"])
                    )

            self.conn.commit()
            print("Database successfully updated.")

        except Exception as e:
            print(f"An error occurred during database processing: {e}")
            if self.conn:
                self.conn.rollback()
        finally:
            cursor.close()
            
    def update_ebay_listings(self, product_id, ebay_listings):
        """
        deletes old eBay data for a product and inserts the new listings
        """
        if not self.conn:
            print("Cannot process data, no database connection.")
            return

        cursor = self.conn.cursor()
        try:
            # remove old listings for this product
            print(f"Deleting old eBay listings for product_id: {product_id}")
            cursor.execute(
                "DELETE FROM deal_board_ebaylisting WHERE product_id = %s;",
                (product_id,)
            )

            # insert the new listings we just scraped
            for listing in ebay_listings:
                print(f"Inserting new eBay listing: {listing['title'][:40]}...")
                cursor.execute(
                    """
                    INSERT INTO deal_board_ebaylisting
                    (product_id, title, subtitle, price, source_url, image_url, scraped_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW());
                    """,
                    (
                        product_id,
                        listing["title"],
                        listing.get("subtitle"),
                        listing["price"],
                        listing["source_url"],
                        listing["image_url"],
                    )
                )
            
            self.conn.commit()
            print(f"Database successfully updated with eBay listings for product_id: {product_id}")

        except Exception as e:
            print(f"An error occurred during eBay listing processing: {e}")
            if self.conn:
                self.conn.rollback()
        finally:
            cursor.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()