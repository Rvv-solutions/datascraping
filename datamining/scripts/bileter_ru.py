from datetime import datetime
from typing import Optional
from datamining.module.controller import Parser
from bs4 import BeautifulSoup
import requests

        
class Bileter(Parser):
    def __init__(self):
        super().__init__()
        self.delay = 1800
        self.driver_source = None
        self.headers = {
            'authority': 'www.bileter.ru',
            'accept': 'text/html, */*; q=0.01',
            'accept-language': 'ru,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'referer': 'https://www.bileter.ru/afisha',
            'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "YaBrowser";v="23"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-pjax': 'true',
            'x-pjax-container': '#js_id_afisha_performances_grid',
            'x-requested-with': 'XMLHttpRequest',
        }
        self.urls = [
            #'https://www.bileter.ru/afisha?building[]=aleksandrinskiy_teatr.html', # Александрийский театр
            #'https://www.bileter.ru/afisha?building[]=bolshoy_dramaticheskiy_teatr_imgatovstonogova.html', # БДТ Товстогонова
            # 'https://www.bileter.ru/afisha?building[]=dom_ofitserov.html', # Дом офицеров
            'https://www.bileter.ru/afisha?building[]=bolshoy_kontsertnyiy_zal_oktyabrskiy.html' # БКЗ "Октябрьский"
        ]
        
    def reformat_venue(self, venue: str) -> Optional[str]:
        return {
            'Александрийский театр': 'Александрийский театр!'
        }.get(venue, None)
        
    def month_string_to_number(self, month):
        return {
            'Января': 1, 'Февраля': 2, 'Марта': 3, 'Апреля': 4,
            'Мая': 5, 'Июня': 6, 'Июля': 7, 'Августа': 8,
            'Сентября': 9, 'Октября': 10, 'Ноября': 11, 'Декабря': 12
        }[month]
        
    def str_to_datetime(self, date : str) -> datetime:
        date_parts = date.split()
        # Извлекаем день, месяц и время
        day = date_parts[0]
        if "Открытая дата" in date: # Если точной даты не существуеты
            return None
        day = int(day)
        month_string = date_parts[1].replace(',', '')
        month_number = self.month_string_to_number(month_string)
        time = date_parts[-1]
        year = date_parts[-2].replace(',', '')
        if month_string == year: # Если не указан год
            year = datetime.now().year
        # Собираем все в datetime объект
        final_date = datetime(year=int(year), month=month_number, day=day, hour=int(time.split(':')[0]), minute=int(time.split(':')[1]))
        return final_date


    def get_date(self, event : BeautifulSoup):
        date = event.find('div', class_='date').text
        datetime_date = self.str_to_datetime(date)
        return datetime_date


    def get_link(self, event : BeautifulSoup) -> str:
        price_block = event.find('div', class_='price')
        link = "https://www.bileter.ru" + price_block.find('a')['href']
        return link


    def get_date_from_list(self, event : BeautifulSoup) -> datetime:
        date_and_price = event.find('a')
        date = date_and_price.contents[0]
        datetime_date = self.str_to_datetime(date)
        return datetime_date


    def get_link_from_list(self, event : BeautifulSoup) -> str:
        return "https://www.bileter.ru" + event.find('a')['href']
    
    
    def put_db(self, events : list[tuple]) -> None: 
        for event in events:
            self.debug(event)
            self.register_event(event_name=event[0], link=event[1], date=event[2], venue=event[3])
            
        
    async def run(self):
        events_list = []
        
        for page in range(100):
            
            for url in self.urls:
                url += f'&page={page}'
                
                r = requests.get(url, headers=self.headers)

                page += 1
                
                soup = BeautifulSoup(r.text, 'lxml')
                
                p = soup.find('p', class_='uppercase')
                
                if p is not None:
                    #self.debug("Done")
                    return

                events = soup.find_all('div', class_='afishe-item')

                for event in events:
                    title = event.find('div', class_='name').text.replace('\n', '')
                    venue = event.find('div', class_='place').text.replace('\n', '')[:-1]
                    
                    tickets : list[BeautifulSoup] = event.find_all('li')
                    if len(tickets) == 0:
                        link = self.get_link(event)
                        date = self.get_date(event)
                        
                        events_list.append((title, link, date, venue))
                    else:
                        for ticket in tickets:
                            link = self.get_link_from_list(ticket)
                            date = self.get_date_from_list(ticket)
                            
                            events_list.append((title, link, date, venue))
            self.debug(events_list)
            self.put_db(events_list)