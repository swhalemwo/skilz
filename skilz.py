
# import code from other litanai (python files are symlinked)
import random

from jutils import *
from openalex import ingest_dispatcher, ingest_csv, pickle_entity, pickle_load_entity, dl_pages
from flatten_openalex_jsonl import flatten_works, init_dict_writer

import clickhouse_connect

from pyalex import Works
from globs import *

import os
from scidownl import scihub_download

from fp.fp import FreeProxy


def dl_author_works (oa_author_id):

    nbr_works = Works().filter(author = {'id' : "https://openalex.org/A5049386877"}).count()
    pager = Works().filter(author = {'id' : "https://openalex.org/A5049386877"}).paginate(per_page=200, n_max = None)
    
    l_works = dl_pages(pager, nbr_works)
    
    return(l_works)

def proc_author_works (oa_author_id, switch_ingest):
    
    id_author_short = oa_author_id.replace('https://openalex.org/', '')
    print(f"id_author_short: {id_author_short}")

    if id_author_short + ".json.gz" not in os.listdir(DIR_AUTHOR_GZIP):
        print("downloading papers")
        l_papers = dl_author_works(oa_author_id)
        pickle_entity(l_papers, id_author_short, DIR_AUTHOR_GZIP)
        b_data_fresh = True
        
    else:
        # only load papers if they are to be ingested, else skip
        if switch_ingest == "always" :
            l_papers = pickle_load_entity(id_author_short, DIR_AUTHOR_GZIP)
        else:
            l_papers = []
            
        print(f"retrieved {len(l_papers)} from file")
        b_data_fresh = False


    l_entities_to_ingest = ['works', 'works_authorships'] #  'works_related_works', 'works_referenced_works']
    ingest_dispatcher(l_papers, l_entities_to_ingest, switch_ingest, b_data_fresh, flatten_works)

    # update flag to see which dois are available for download
    # uses some convoluted logic to need less memory/time: first filter down sci-hub dois with works,
    # then use those to update
    # FIXME: could add filter to only search for those of current oa_author_id
    
    cmd_update = """ALTER TABLE works
    (UPDATE doi_in_scihub = 1 WHERE replaceOne(doi, 'https://doi.org/', '') IN (
        SELECT doi FROM scihub_doi
        WHERE doi IN (
            SELECT replaceOne(doi, 'https://doi.org/', '')
            FROM works
        )
    ))"""

    ch_client = clickhouse_connect.get_client(database = DBNAME)

    ch_client.command(cmd_update)


def dl_doi_ppb(doi, id_work, proxy):
    "generate command for PyPaperBot"

    # if f"{doi}.pdf" not in os.listdir(DIR_PDF):
    # breakpoint()

    # cmd_dl = f"scidownl download --doi '{doi}' --out {os.path.join(DIR_PDF, id_work_proc)}.pdf"
    
    # print(cmd_dl)
    # subprocess.run(cmd_dl, shell=True)

    # proxies = {'http' : "3.37.125.76:3128"}
    proxies = {'http' : proxy}

    # doi = "https://doi.org/10.1177/1363459309360783"
    # id_work_proc = "W2169290678"
    id_work_proc = id_work.replace("https://openalex.org/", "")

    try: 
        scihub_download(doi, paper_type = "doi", out = os.path.join(DIR_PDF, id_work_proc) + ".pdf", proxies = proxies)


        global DBNAME
        cmd_update_dl_info = f"ALTER TABLE works update pdf_downloaded = 1 where id = 'https://openalex.org/{id_work_proc}'"

        ch_client = clickhouse_connect.get_client(database = "skilz")
        ch_client.command(cmd_update_dl_info)
        print("done")
        return True

    except:
        print(f'Error downloading {doi} with proxy {proxy}: {e}')
        return False

        

    


def get_random_proxies(count):
    print("getting proxies...")
    proxies = []
    for _ in range(count):
        proxy = FreeProxy(rand=True).get()
        proxies.append(proxy)
    return proxies



def download_papers(l_dois, l_work_ids):
    # Initial proxy setup
    # breakpoint()
    good_proxies = get_random_proxies(8)  # Start with 10 random proxies
    # good_proxies = ['http://13.37.59.99:3128', 'http://3.12.144.146:3128', 'http://3.122.84.99:3128', 'http://65.1.40.47:3128', 'http://204.236.137.68:80', 'http://3.127.62.252:80', 'http://204.236.176.61:3128', 'http://44.218.183.55:80', 'http://3.90.100.12:80', 'http://3.90.100.12:80']
    bad_proxies = []
    max_attempts = 5
    downloads = {doi: False for doi in l_dois}  # Track download statuses
    
    for doi, work_id in zip(l_dois, l_work_ids):
        attempt = 0
        while not downloads[doi] and attempt < max_attempts:
            # Randomly select a proxy from the list
            proxy = random.choice(good_proxies)
            
            
            if dl_doi_ppb(doi, work_id, proxy):
                downloads[doi] = True  # Mark this DOI as downloaded
            else:
                # Remove proxy if it fails
                bad_proxies.append(proxy)
                good_proxies.remove(proxy)
                print(f'Removed proxy {proxy}. {len(good_proxies)} left.')
            
            attempt += 1
        
        if not downloads[doi]:  # If after attempts the DOI is still not downloaded
            print(f'Failed to download {doi} after {max_attempts} attempts.')
        
        # If proxies are running low, refresh the list
        if len(good_proxies) < 5:  # Example threshold
            print('Refreshing proxies...')
            new_proxies = set(get_random_proxies(10))  # Get new proxies
            new_proxies_filtered = new_proxies - set(bad_proxies) # yeet bad proxies
            good_proxies = good_proxies + list(new_proxies_filtered)
            

            
            
    print('Download statuses:', downloads)



    

def dl_author_pdfs(oa_author_id):
    "download works of an author from sci-hub"

    # breakpoint()
    # check which works already are downloaded
    # would be best to keep track of this in the works table -> update after each download
    
    # get articles to download
    cmd_articles_to_dl = f"""SELECT id, doi from works where id in
    (SELECT work_id from works_authorships where author_id = '{oa_author_id}')
    and pdf_downloaded = 0 and doi_in_scihub = 1"""

    print(cmd_articles_to_dl)

    ch_client = clickhouse_connect.get_client(database = "skilz")
    dt_dois_to_dl = ch_client.query_df(cmd_articles_to_dl)
    
    download_papers(dt_dois_to_dl['doi'].to_list(), dt_dois_to_dl['id'].to_list())
    # check which ones are available on sci-hub
    
    


# def gc_ingest_cmd (entity, DIR_CSV):
#     cmd = f"""clickhouse-client -d skilz --query "INSERT INTO {entity} FROM INFILE '{DIR_CSV}{entity}.csv.gz' COMPRESSION 'gzip' FORMAT CSV\""""

#     return (cmd)



# patrick brown
# proc_author_works("https://openalex.org/A5049386877", switch_ingest = "always")


dl_author_pdfs("https://openalex.org/A5049386877")









