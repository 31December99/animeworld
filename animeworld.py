import logging
import asyncio
import random
import re

from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from database import Database


class Page:
    """
        Carica l'indice della pagina anime di https://www.animeworld.so
        Filtro anime/doppiato ecc vedere link su browser dopo aver selezionato tipo di filtro.
        """

    @staticmethod
    def get_newagent():
        uastrings = [
            "Mozilla/6.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.111 "
            "Safari/537.36",
            "Mozilla/6.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 "
            "Safari/537.36",
            "Mozilla/6.0 (Macintosh; Intel Mac OS X 10_10) AppleWebKit/600.1.25 (KHTML, like Gecko) Version/8.0 "
            "Safari/600.1.25",
            "Mozilla/6.0 (Windows NT 6.1; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0",
            "Mozilla/6.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.111 "
            "Safari/537.36",
            "Mozilla/6.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/38.0.2125.111 Safari/537.36",
            "Mozilla/6.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/600.1.17 (KHTML, like Gecko) Version/7.1 "
            "Safari/537.85.10",
            "Mozilla/6.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/6.0 (Windows NT 6.3; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0",
            "Mozilla/6.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.104 "
            "Safari/537.36"
        ]
        return random.choice(uastrings)

    def __init__(self, page_number: int, url: str):
        self.headers = {'User-Agent': self.get_newagent()}
        self.page_number = page_number
        self.url = url
        self.episodes_index = []
        self._page_index = []
        self._myanimelist = []

    # data
    async def _get_links_index(self) -> list:
        """

        Ottiene un indice con tutti i link delle serie anime di una data pagina
        Estrae solo gli attributi 'DIV' di classe 'film-list' ovvero dove sono elencati i link dell'indice.
        Quindi il resto della pagina lo esclude dalla ricerca.
        attributo 'data-jtitle' (titolo)
        attributo 'href'  ( link)

        :return:
        """

        req = Request(self.url, headers=self.headers)
        html_page = urlopen(req)
        soup = BeautifulSoup(html_page, 'html.parser')
        film_list = soup.find_all('div', {'class': 'film-list'})

        for a in film_list:
            c = a.find_all('a', {'class': 'name'})
            for t in c:
                # <class ="name" data-jtitle="Lady Georgie" href="/play/georgie.9PoM7" > Georgie < / a >
                logging.debug(f"------------> {t.text} {t['data-jtitle']}")
                # Mette in elenco il titolo visualizzata sulla pagina e "alternativo" in html
                self._page_index.append([f"https://www.animeworld.so{t['href']}", t.text, t['data-jtitle']])
                logging.info(f"Titolo: {t.text}   https://www.animeworld.so{t['href']}")
        return self._page_index

    async def _get_title_from_link(self, myanime_link):
        req = Request(myanime_link, headers=self.headers)
        html_page = urlopen(req)
        soup = BeautifulSoup(html_page, 'html.parser')

        second_title = soup.find_all('p', {"class": 'title-english title-inherit'})
        if second_title:
            second_title = second_title[0].getText()
        main_title = soup.find_all('h1', {"class": 'title-name h1_bold_none'})[0].getText()
        return [main_title, second_title]

    async def get_index(self) -> list:
        """
        Crea un elenco con all'interno:
        titolo 1 myanimelist , titolo 2 myanimelist, titolo animeworld, link play (link della serie
        che contiene i link degli episodi

        :return:
        """
        self._page_index = await self._get_links_index()
        for play_link, title, jtitle in self._page_index:
            req = Request(play_link, headers=self.headers)
            title = title.lower()
            title = title.replace('(ita)', '').strip().lower()
            jtitle = jtitle.lower()
            jtitle = jtitle.replace('(ita)', '').strip().lower()
            self._myanimelist.append([title, play_link, jtitle])
        return self._myanimelist


class Animeworld(Page):

    def __init__(self, page_number: int, url: str):
        super().__init__(page_number, url)
        # Elenco di tutti gli episodi di ogni titolo compreso nell'indice di page_number
        self._episodes_index = []
        # Elenco di tutti i link diretti al download per ogni episodio nell'indice _episodes_index[]
        self.download_links = []

    async def get_ep(self, url_ep: str) -> str:

        try:
            split = url_ep.split('/')
            ep_str = split[-1]
            res = re.search(r"_[^A-z-]\d+", ep_str, re.IGNORECASE)
            res = res.group().replace('_', '')
            return res
        except Exception as e:
            logging.info(f"get_ep_error : {e} {url_ep}")
            return '-1'

    async def get_season(self, url_ep: str) -> str:

        try:
            split = url_ep.split('/')
            ep_str = split[-1]
            ep_str = ep_str.lower()
            res = re.search(r"[^a-z-]+_Ep", ep_str, re.IGNORECASE)
            if res:
                res = res.group().replace('_ep', '')
                # Oltre lo interpreta come il valore di un anno..
                if int(res) < 1100 and int(res) != 0:
                    return res
            return '1'
        except Exception as e:
            logging.info(f"get_season_error : {e} {url_ep}")
            return '-1'

    async def get_new_link(self, link: str) -> bool:
        """
        individua una parola e ritorna l'esito
        """
        _new_link = link.lower().split('_')
        if 'sub' in _new_link:
            return False
        else:
            return True

    async def get_buttons_link(self, url_ep: str, title_ep: str, log: bool) -> list:
        """
        Prende in input un link dell'indice episodi esempio https://www.animeworld.so/play/one-piece-ita.d5nah/HwqGar
        e ritorna i links diretti per il download di tutti gli episodi disponibili
        Carica le tutte le tabelle non solo quella della pagina corrente...Dividono le stagioni in più pagine (?)
        """
        # Creo una query con tutte le tabelle presenti nel database
        database = Database("animeworld.db")
        await database.connect()
        cursor = await database.db.execute(f"SELECT * from sqlite_master WHERE type='table'", )
        rows = await cursor.fetchall()
        query = ''
        for r in rows:
            if 'animes' in r[1]:
                query = query + f"SELECT download_links,title1 from {r[1]} UNION "
        # Rimuovo ultimo 'union'
        query = query[:-6]
        # Carico tutte le pagine con i video già presenti in Plex
        cursor = await database.db.execute(f"{query}", )
        rows = await cursor.fetchall()
        last_ep = 0
        last_seas = 0
        for r in rows:
            if r[1].isspace() is False:
                if title_ep in r[1]:
                    last_ep = await self.get_ep(r[0])
                    last_seas = await self.get_season(r[0])
        req = Request(url_ep, headers=self.headers)
        html_page = urlopen(req)
        soup = BeautifulSoup(html_page, 'html.parser')
        _titles = ['', '']
        _episodesN = 0
        _episodes_buttons_links = []

        # Controlla sempre solo il primo video per capire da quale season/episode inizia
        result = soup.find_all('a', {"data-base": 1})
        if not result:
            return _episodes_buttons_links
        url = f"https://www.animeworld.so{result[0]['href']}"
        url_season = await self.get_season(url)
        # Se la season disponibile da animeword è la stessa del db allora assegna il numero di episodio da dove
        # inizare a leggere gli urls
        # Se la season disponibile di animword non è la stessa del db inizierà dal primo episodio
        if url_season == last_seas:
            _episodesN = int(last_ep)
        while True:
            _episodesN = _episodesN + 1
            result = soup.find_all('a', {"data-base": _episodesN})
            if not result:
                break
            if log:
                logging.info(f"Button Pagina episodio n°{_episodesN} :: https://www.animeworld.so{result[0]['href']}")
            _episodes_buttons_links.append([f"https://www.animeworld.so{result[0]['href']}", f"{title_ep}"])
            await asyncio.sleep(1)
        return _episodes_buttons_links

    async def get_download_episode_link(self, url_ep: str, title1: str, jtitle: str) -> list:

        req = Request(url_ep, headers=self.headers, unverifiable=False)
        html_page = urlopen(req)
        soup = BeautifulSoup(html_page, 'html.parser')
        download = soup.find_all('div', {"id": "download"})

        for link in download:
            result = link.find_all('a')
            # Ci sono tre tipi di download ( diretto , alternativo, esterno)
            # Con l'alternativo è possibile subito accedere al file senza analizzare un'altra pagina...
            for r in result:
                if 'download alternativo' in r.text.lower():
                    # Esclude dalla lista i link che contengono determinate parole
                    if await self.get_new_link(r['href']):
                        logging.info(f"{r['href']}")
                        self.download_links.append([r['href'], title1, jtitle])
                await asyncio.sleep(0.4)
        return self.download_links

    async def download(self):
        titles = await self.get_index()
        for title, play_link, jtitle in titles:
            logging.info(f'\n> TITLE: {title} JTITLE: {jtitle} {play_link}')
            # Ottengo il link al download da ogni pagina button
            button_links = await self.get_buttons_link(url_ep=play_link, title_ep=title, log=True)
            # Successivamente ottengo link diretto dal button "download alternativo" di ogni pagina button
            for button_link, *_ in button_links:
                await self.get_download_episode_link(url_ep=button_link, title1=title, jtitle=jtitle)

        return self.download_links

