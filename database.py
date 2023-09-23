import aiosqlite


class Database:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.db = None

    async def connect(self):
        self.db = await aiosqlite.connect(self.file_name)
        return self.db

    async def _insert(self, download_links, table, title1, jtitle):
        if not download_links:
            return False
        try:
            await self.db.execute(f"INSERT INTO {table} (download_links,title1,jtitle)"
                                  f" VALUES (?,?,?)",
                                  (download_links, title1, jtitle))
        except Exception as w:
            print(w)

    async def add_storj_account(self, api_key: str, satellite: str, password: str, email: str, passphrase: str,
                                serialize_accessgrant: str):

        try:
            await self.db.execute(f"INSERT INTO accounts (my_email,my_password,my_satellite,my_api_key, passphrase,"
                                  f"serialize_accessgrant) VALUES (?,?,?,?,?,?)",
                                  (email, password, satellite, api_key, passphrase, serialize_accessgrant))
            await self.db.commit()
        except Exception as w:
            print(w)

    async def load_storj_account(self, db_id: str):

        cursor = await self.db.execute(
            f"SELECT my_email,my_password,my_satellite,my_api_key,passphrase,serialize_accessgrant"
            f" FROM accounts WHERE id=?", (db_id,))
        row = await cursor.fetchone()
        my_email, my_password, my_satellite, my_api_key, passphrase, serialize_accessgrant = row

        return {'my_email': my_email, 'my_password': my_password, 'my_satellite': my_satellite,
                'my_api_key': my_api_key, 'passphrase': passphrase, 'serialize_accessgrant': serialize_accessgrant}

    async def save_page(self, download_links, table: str):
        for link, title1, jtitle in download_links:
            await self._insert(link, table, title1, jtitle)
        await self.db.commit()

    async def load_titles(self, table: str) -> list:

        cursor = await self.db.execute(f"SELECT title1,jtitle from {table}")
        rows = await cursor.fetchall()
        if not rows:
            print(f"Tabella {table} vuota o inesistente !")
        return rows

    async def load_download_titles(self, table: str) -> list:

        cursor = await self.db.execute(f"SELECT download_links,plex_title,title1,jtitle,librerie from {table}"
                                       f" WHERE (upload='Download' or upload is NULL)")
        rows = await cursor.fetchall()
        if not rows:
            print(f"Tabella {table} vuota o inesistente !")
        return rows

    async def load_page_download_link(self, table: str, title: str) -> list:
        try:
            cursor = await self.db.execute(f"SELECT download_links from {table} WHERE plex_title=?", (title,))
            rows = await cursor.fetchall()
            if not rows:
                print(f"Tabella [{table}] nessun titolo '{title}'")
            return rows
        except Exception as e:
            print(e)

    async def load_urls(self, table: str) -> list:
        cursor = await self.db.execute(f"SELECT download_links from {table}")
        _urls = await cursor.fetchall()
        return [i[0] for i in _urls]

    async def update_db_from_urls(self, table: str):
        """
        Aggiorna i gli url su sqlite come uploadati
        in realtà andrebbere verificati almeno i files nel bucket di storj..
        """
        cursor = await self.db.execute(f"SELECT download_links from {table}")
        urls = await cursor.fetchall()
        result_to_list = [i[0] for i in urls]

        for url in result_to_list:
            await self.db.execute(f"UPDATE upload from {table} WHERE download_links=?",
                                  (url,))  # ?? query errata upload cosa?
            await self.db.commit()

    async def save_plex_results(self, download_link: str, table: str, status: str, library: list):
        # Prende il nome della serie solo una volta escludendo tutte le altre seasons
        library_name = []
        for lib in library:
            library_name.append(lib.librarySectionTitle)
        await self.db.execute(f"UPDATE {table} SET upload=?, librerie=? WHERE download_links=?",
                              (status, ':'.join(library_name), download_link,))

    async def update_plex_status(self, download_link: str, table: str):
        await self.db.execute(f"UPDATE {table} SET upload='' WHERE download_links=?", (download_link,))
        await self.db.commit()

    async def create_table_page(self, table: str):

        page_table = f"""CREATE TABLE IF NOT EXISTS {table} (
                        id             INTEGER PRIMARY KEY AUTOINCREMENT
                                               UNIQUE
                                               NOT NULL,
                        download_links TEXT UNIQUE,
                        plex_title TEXT,
                        upload         TEXT,                        
                        title1         TEXT,
                        jtitle         TEXT,
                        librerie       TEXT
                    );"""

        await self.db.execute(page_table)

    async def close(self):
        await self.db.close()

