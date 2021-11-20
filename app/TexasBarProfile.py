# TexasBarProfile.py - Retrieve Texas Bar Profile from www.texasbar.com

import requests

from bs4 import BeautifulSoup

class TexasBarProfile():
    """
    Retrieve attorney profile from www.texasbar.com
    """
    def __init__(self):
        """
        Class initializer.

        Args:
            None
        """
        self.url = 'https://www.texasbar.com/AM/Template.cfm?Section=Find_A_Lawyer&Template=/CustomSource/MemberDirectory/Result_form_client.cfm'
        self.data = {
            'PPlCityName': '',
            'County': '',
            'State': '',
            'Zip': '',
            'Name': '',
            'CompanyName': '',
            'BarCardNumber': '',
            'Submitted': '1',
            'ShowPrinter': '1',
            'Find': '0'
        }

    def retrieve(self, city:str = '', county:str = '', state:str = '', zip:str = '', name:str = '', company:str = '', barcard:str = ''):
        """
        Retrieve the HTML page for the given attorney from the web site.

        Args:
            city (str): City Name to search for
            county (str): County Name to search for
            state (str): State abbreviation to search for
            zip (str): ZIP Code to search for
            name (str): Attorney name to search for
            company (str): Company or Firm Name to search for
            barcard (str): Bar card number to search for
        
        Results:
            (str): String content retrieved from site
        """
        self.data['PPlCityName'] = city
        self.data['County'] = county
        self.data['State'] = state
        self.data['Zip'] = zip
        self.data['Name'] = name
        self.data['CompanyName'] = company
        self.data['BarCardNumber'] = barcard

        result = requests.post(self.url, data=self.data)
        return result

    def parse(self, result) -> list:
        """
        Parse content retrieved from web site.

        Args:
            result: Result from self.retrieve()

        Returns:
            (list): List of dict of Attorney profile
        """
        soup = BeautifulSoup(result.content, "html.parser")
        lawyers = soup.find_all("article", class_="lawyer")
        result = [lawyer for lawyer in self.extract(lawyers)]
        return result

    def extract(self, lawyers) -> list:
        """
        Extract a lawer from each item in the lawers list
        """
        for lawyer in lawyers:
            fname = ''
            mname = ''

            prefix = lawyer.find('span', class_='honorific-prefix')
            gnames = lawyer.find_all('span', class_='given-name')
            if gnames:
                fname = gnames[0]
            if len(gnames) > 1:
                mname = gnames[1]
            additional_name = lawyer.find('span', class_='additional-name')
            lname = lawyer.find('span', class_='family-name')
            suffix = lawyer.find('span', class_='honorific-suffix')
            firm = lawyer.find('h5')
            address = parse_address(lawyer.find('p', class_='address'))
            telephone = lawyer.find('a', href=lambda x: "tel:" in x.lower()).text.strip()
            yield {
                'prefix': prefix.text.strip(),
                'fname': fname.text.strip(),
                'mname': mname.text.strip(),
                'lname': lname.text.strip(),
                'suffix': suffix.text.strip(),
                'firm': firm.text.strip(),
                'address': address,
                'familiar_name': additional_name.text.strip()[1:-1],
                'telephone': telephone.replace('Tel: ', '')
            }


def parse_address(address: str) -> dict:
    """
    Parse an address string into a dict of subparts.
    """
    parts = [child.text.strip() for child in address.children]
    street = parts[0]
    parts = parts[1].split(',')
    city = parts[0]
    parts = parts[1].split('\xa0')
    state = parts[0]
    zip = parts[1]
    return {
        'street': street,
        'city': city,
        'state': state,
        'zip': zip
    }

def main():
    searcher = TexasBarProfile()
    result = searcher.retrieve(barcard='24059643')
    attorneys = searcher.parse(result)
    for attorney in attorneys:
        print(attorney)

if __name__ == '__main__':
    main()
