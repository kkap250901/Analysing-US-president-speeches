
import pandas as pd
from bs4 import BeautifulSoup
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
soup = BeautifulSoup(driver.page_source, 'html.parser')


def speech_urls(url : str = 'https://millercenter.org/the-presidency/presidential-speeches', sleep_time : int = 3) -> list:
    '''
    This function is to get the specific url for each speech
    '''
    driver.get(url=url)
    initial_coor = driver.execute_script("return document.body.scrollHeight") 
    for i in range(100):
        # Scrolling all the way down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")#
        time.sleep(sleep_time)
        new_coordinate = driver.execute_script("return document.body.scrollHeight")
        if new_coordinate == initial_coor:
            break 
        initial_coor = new_coordinate

    # Getting the speech titles here 
    speeches = []

    bs = BeautifulSoup(driver.page_source, 'html.parser')
    parsed = bs.find_all('div', class_ = 'views-row')
    driver.quit()
    for speech_titles in parsed:
        endings = speech_titles.find('a')['href'][38:]
        speeches.append(endings)
    
    return speeches


def full_speech(base_url : str = 'https://millercenter.org/the-presidency/presidential-speeches/') -> pd.DataFrame:
    """
    This funciton here gets the sppeches from the specif link, but not only speeches it also gets 
    the presidents :
    * `Name`
    * `Date of speech`
    * `Speech Transcript`
    """
    president = {}
    speech_url = speech_urls()
    urls = [base_url + x for x in speech_url]

    for url in urls:
        result = requests.get(url=url)
        result_text = result.text
        soup = BeautifulSoup(result_text,'html.parser')
        name = soup.find(class_ = 'president-name').text
        date = soup.find(class_ = 'episode-date').text
        transcript = soup.find(class_="view-transcript").text[10:] # This is because the first part is the title 
        try : 
            summary = soup.find(class_ = 'about-sidebar--intro').text
        except : 
            summary = ''
        title = soup.find(class_ = 'presidential-speeches--title').text.split(':')[1][1:]
        president.update({url : [name, date, title, summary, transcript]})

    presidentdf = pd.DataFrame(president)
    presidentdf = presidentdf.T
    presidentdf.columns = ['Name', 'Date', 'Title', 'Speech_Summary', 'Speech']
    presidentdf = cleaningSpeeches(speechdf= presidentdf)

    return presidentdf


def cleaningSpeeches(speechdf : pd.DataFrame) -> pd.DataFrame:
    """
    This here is just to clean speeches with some weird layouts observed in the most recent president transcripts
    """
    speechdf = speechdf.replace({"\n" : ''},regex=True)
    speechdf['Speech'] = speechdf['Speech'].replace({"anscript" : ' '},regex=True)
    speechdf['Speech'] = speechdf['Speech'].replace({"Tr" : ' '},regex=True)
    speechdf = speechdf.replace({'\r':''},regex=True)

    return speechdf


def wiki_data(url : str = "https://en.wikipedia.org/wiki/List_of_presidents_of_the_United_States") -> pd.DataFrame:
    """
    This function extra detail about president such as:
    * `Term start`
    * `Term end`
    * `Party affiliation`
    """
    presidentdf = pd.read_html(url)[0]
    presidentdf = presidentdf[['Name (Birth–Death)', 'Term[14]', 'Party[b][15].1']]
    presidentdf.columns = ['Name', 'Term', 'Party']
    presidentdf = presidentdf.replace("([\(\[]).*?([\)\]])","",regex = True)
    presidentdf['From'] = presidentdf['Term'].apply(lambda x: (pd.to_datetime(x.split("–")[0])).year)
    presidentdf = presidentdf.replace({'Incumbent' : '2022'}, regex= True)
    presidentdf['To'] = presidentdf['Term'].apply(lambda x: (pd.to_datetime(x.split("–")[1])).year if str(x.split("–")[1]) != "Incumbent" else "2021")
    presidentdf = presidentdf.drop(columns=['Term'])
    presidentdf['Party'] = presidentdf['Party'].replace({'Democratic- Republican National Republican' : 'Democratic- Republican',
                                                        'Whig Unaffiliated' : 'Whig',
                                                        'Republican National Union' : 'Republican',
                                                        'National Union Democratic' : 'Democratic'})
                                                        
    presidentdf['Name'] = presidentdf['Name'].apply(lambda x : str(x)[:-2])

    # Changing names which are not the same in both data sources
    presidentdf = presidentdf.replace({"Richard Nixon":"Richard M. Nixon","William Howard Taft":"William Taft","William Henry Harrison":"William Harrison"}, regex=True)

    return presidentdf


def everything() -> pd.DataFrame:
    '''
    Getting all the data together and merged into one dataframe
    '''
    speechesdf = full_speech()
    wikidf = wiki_data()
    Overalldf = pd.merge(wikidf,speechesdf,how='inner',on='Name')

    return Overalldf


if __name__ == '__main__':
    df = everything()
    # df.drop(columns='Unnamed: 0',inplace=True)
    df.to_csv('US-president-speeches-with-metadata-test.csv')

