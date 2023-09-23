#!/usr/bin/env python3.9

import asyncio
import logging
from database import Database
from animeworld import Animeworld

# LOG
logging.basicConfig(level=logging.INFO)


class Awbot:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def start(self, mainlink: str, page_n: int, prefix: str):
        """
        :param mainlink: indirizzo link della pagina filtrata per_
                                    stato = incorso
                                    sottotitoli = doppiato
                                    audio = italiano
                                    tipo = anime
                                    Ordine = Ultime aggiunte

        :param page_n: numero della pagina
        :param prefix: prefisso per il database
        :return: void !
        """
        try:

            """
                Dichiaro un nuovo database SQLite
            """
            database = Database("animeworld.db")
            await database.connect()
            table = f"{prefix}{page_n}"

            """
            Creo una nuova tabella nel dbSqlite se non esiste 
            """
            await database.create_table_page(table=table)

            """
            Dichiaro nuova pagina pagina_n 
            """
            page = Animeworld(page_number=page_n, url=f"{mainlink}{page_n}")

            """
            Ottengo l'indice dei links di quella pagina page_n
            """
            download_links = await page.download()

            for link in download_links:
                logging.info(f"{link}")

            """
            Salva su DBsqlite tutti i links nella tabella table
            """
            logging.info("Salvataggio su DB...")
            await database.save_page(download_links=download_links, table=table)

            logging.info(" - Fine aggiornamento URLS-\n")
            await database.close()

        except KeyboardInterrupt:
            pass
        finally:
            pass


if __name__ == "__main__":
    # todo: la selezione della pagina è ancora manuale
    anime_incorso = "https://www.animeworld.so/filter?type=0&status=0&dub=1&language=it&sort=1&page="

    awbot = Awbot()
    awbot.loop.run_until_complete(awbot.start(mainlink=anime_incorso, page_n=1, prefix='anime_incorso'))
