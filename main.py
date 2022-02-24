from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests
import json
import base64
import re

URL = 'https://bimasislam.kemenag.go.id/jadwalimsakiyah'

def fetch(req, url, data=None):
    if data is None:
        return req.get(url).content
    else:
        return req.post(url, data=data).content

def get_states(search=None):
    f= open("states/all.json","r")
    states = json.load(f)
    f.close()

    if search is not None and len(search) > 0:
        states = list(filter(lambda state: state['name'].find(search.upper()) > -1, states))

    if len(states) == 0:
        raise HTTPException(status_code=404, detail="State not found")

    return states

def get_cities(stateId, search=None):
    cities = []

    states = get_states()
    selectedState = list(filter(lambda s: s['id'] == stateId, states))

    if len(selectedState) == 0:
        raise HTTPException(status_code=404, detail="State not found")

    try:
        f= open("cities/{stateId}.json".format(stateId=stateId),"r")
        cities = json.load(f)
        f.close()
    except:
        req = requests.Session()
        soup = BeautifulSoup(fetch(req, URL), 'html.parser')

        formdata = dict()
        formdata['x'] = selectedState[0]['code']

        posturl = 'https://bimasislam.kemenag.go.id/ajax/getKabkoshalat'

        r = req.post(posturl, data=formdata)

        soupCities = BeautifulSoup(r.text, 'html.parser')
        options = soupCities.find_all('option')

        tempId = 1

        for option in options:
            cities.append({
                'id': tempId,
                'code': option.get('value'),
                'name': option.text,
                'state': selectedState[0]
            })
            tempId += 1
    
        with open("cities/{stateId}.json".format(stateId=stateId), 'w') as f:
            json.dump(cities, f)

    # searching
    if search is not None and len(search) > 0:
        cities = list(filter(lambda city: city['name'].find(search.upper()) > -1, cities))

    return cities


def get_imsyakiyah(stateId, cityId, year, date=None):
    imsyakiyah = []
    fileId = "{year}_{cityId}".format(year=year, cityId=cityId)

    cities = get_cities(stateId)
    selectedCity = list(filter(lambda c: c['id'] == cityId, cities))

    if len(selectedCity) == 0:
        raise HTTPException(status_code=404, detail="City not found")

    try:
        f= open("imsyakiyah/{fileId}.json".format(fileId=fileId),"r")
        imsyakiyah = json.load(f)
        f.close()
    except:
        req = requests.Session()
        soup = BeautifulSoup(fetch(req, URL), 'html.parser')

        formdata = dict()
        formdata['x'] = selectedCity[0]['state']['code']
        formdata['y'] = selectedCity[0]['code']
        formdata['thn'] = year

        posturl = 'https://bimasislam.kemenag.go.id/ajax/getImsyakiyah'

        r = req.post(posturl, data=formdata)

        data = json.loads(r.text)

        if data['message'] == "Success":
            imsyakiyah = data
            with open("imsyakiyah/{fileId}.json".format(fileId=fileId), 'w') as f:
                json.dump(imsyakiyah, f)

    meta = {
        'state': imsyakiyah['prov'],
        'city': imsyakiyah['kabko'],
        'year': year,
        'latitude': imsyakiyah['lintang'],
        'longitude': imsyakiyah['bujur'],
        'hijri': imsyakiyah['hijriah'],
    }

    custom_data = []

    if date is not None:
        selected = imsyakiyah['data'][date]
        custom_data.append({
                'date': selected['tanggal'],
                'imsak': selected['imsak'],
                'subuh': selected['subuh'],
                'syuruk': selected['terbit'],
                'dhuha': selected['dhuha'],
                'dzuhur': selected['dzuhur'],
                'ashar': selected['ashar'],
                'maghrib': selected['maghrib'],
                'isya': selected['isya'],
            })
    else:
        for key in imsyakiyah['data']:
            d = imsyakiyah['data'][key]
            
            custom_data.append({
                'date': d['tanggal'],
                'imsak': d['imsak'],
                'subuh': d['subuh'],
                'syuruk': d['terbit'],
                'dhuha': d['dhuha'],
                'dzuhur': d['dzuhur'],
                'ashar': d['ashar'],
                'maghrib': d['maghrib'],
                'isya': d['isya'],
            })
    
    if len(custom_data) == 0:
        raise HTTPException(status_code=404, detail="Data not found")

    return {
        'status': True,
        'message': 'Success',
        'data': custom_data,
        'meta': meta,
    }

tags_metadata = [
    {
        "name": "state",
        "description": "Mendapatkan data semua Provinsi.",
    },
    {
        "name": "city",
        "description": "Mendapatkan data semua Kabupaten/Kota berdasarkan Provinsi.",
    },
    {
        "name": "imsyakiyah",
        "description": "Mendapatkan data jadwal Imsyakiyah berdasarkan Provinsi, Kabupaten/Kota dan Tahun.",
    },
]

description = """
API ini merupakan API yang dapat mengambil data jadwal Imsyakiyah berdasarkan Provinsi, Kabupaten/Kota dan Tahun.
Kami menerapkan metode caching sederhana dengan menyimpan data yang pernah di request ke dalam file json.
Sehingga diharapkan data yang sudah di request tidak perlu di request kembali dan tidak membebani situs dimana kami memperoleh data.
Silahkan gunakan API ini dengan bijak. Jika ada kritik dan saran bisa mengirimkan pesan melalui email [sakukode@gmail.com](mailto:sakukode@gmail.com) . Terima kasih :).

## Sumber data:
- [Situs Kementerian Agama Republik Indonesia](https://bimasislam.kemenag.go.id/)

## Teknologi yang digunakan:
- [FastAPI](https://fastapi.readthedocs.io/)
- [Requests](https://2.python-requests.org/)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)

"""

app = FastAPI(title='Santrikoding Jadwal Imsyakiyah API', 
    description=description, 
    openapi_tags=tags_metadata,
    docs_url="/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/state', tags=["state"], responses={
    200: {
        'description': 'A State List Response',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'status': {
                            'type': 'boolean'
                        },
                        'message': {
                            'type': 'string',
                            'example': 'Success'
                        },
                        'data': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {
                                        'type': 'integer',
                                        'example': 1
                                    },
                                    'code': {
                                        'type': 'string',
                                        'example': 'q2hLFtgxxMFIriCYsUjR4EyExHaTISM4UM6nqxBPKFw88uqkqgo43hMyKYNzXcNJFZ8mHPI4bsovvnWwj2MXhA%3D%3D'
                                    },
                                    'name': {
                                        'type': 'string',
                                        'example': 'PUSAT'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    404: {
        'description': 'Data not found',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'detail': {
                            'type': 'string',
                            'example': 'State not found'
                        }
                    }
                }
            }
        }
    }
})
def read_state(search: Optional[str] = None):
    states = get_states(search)
    return JSONResponse(status_code=200, content={"status": True, "message": "Success", "data": states})

@app.get('/city', tags=["city"], responses={
    200: {
        'description': 'A City List Response',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'status': {
                            'type': 'boolean'
                        },
                        'message': {
                            'type': 'string',
                            'example': 'Success'
                        },
                        'data': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'id': {
                                        'type': 'integer',
                                        'example': 1
                                    },
                                    'code': {
                                        'type': 'string',
                                        'example': 'XyJIzapigzFF7cf9ZnsY2UqPDECqqpLko0gVO1g7hueptr5hj4l01wyIy4Yj%2B2wY%2FcC0SKUUZnLH4uPYQXqeBA%3D%3D'
                                    },
                                    'name': {
                                        'type': 'string',
                                        'example': 'KAB. BANJARNEGARA'
                                    },
                                    'state': {
                                        'type': 'object',
                                        'properties': {
                                            'id': {
                                                'type': 'integer',
                                                'example': 15
                                            },
                                            'code': {
                                                'type': 'string',
                                                'example': '6LoSW8f3n%2F%2FZESP8H%2B5pWRA%2F%2BemLrg67rbWZWm9%2Fx2KZ97lqEpSeRiH94WyxnOQyTNZX%2FEsObmFTFtc26hxbZQ%3D%3D'
                                            },
                                            'name': {
                                                'type': 'string',
                                                'example': 'JAWA TENGAH'
                                            }
                                        }
                                    }   
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    404: {
        'description': 'Data not found',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'detail': {
                            'type': 'string',
                            'example': 'City not found'
                        }
                    }
                }
            }
        }
    }
})
def read_city(stateId: int, search: Optional[str] = None):
    cities = get_cities(stateId, search)
    
    return JSONResponse(status_code=200, content={"status": True, "message": "Success", "data": cities})


@app.get('/imsyakiyah', tags=["imsyakiyah"], responses={
    200: {
        'description': 'A Imsyakiyah List Response',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'status': {
                            'type': 'boolean'
                        },
                        'message': {
                            'type': 'string',
                            'example': 'Success'
                        },
                        'data': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'date': {
                                        'type': 'string',
                                        'example': 'Sabtu, 02/04/2022'
                                    },
                                    'imsak': {
                                        'type': 'string',
                                        'example': '04:19'
                                    },
                                    'subuh': {
                                        'type': 'string',
                                        'example': '04:29'
                                    },
                                    'syuruk': {
                                        'type': 'string',
                                        'example': '05:41'
                                    },
                                    'dhuha': {
                                        'type': 'string',
                                        'example': '06:08'
                                    },
                                    'dzuhur': {
                                        'type': 'string',
                                        'example': '11:49'
                                    },
                                    'ashar': {
                                        'type': 'string',
                                        'example': '15:04'
                                    },
                                    'maghrib': {
                                        'type': 'string',
                                        'example': '18:04'
                                    },
                                    'isya': {
                                        'type': 'string',
                                        'example': '18:58'
                                    }
                                }
                            }
                        },
                        'meta': {
                            'type': 'object',
                            'properties': {
                                'state': {
                                    'type': 'string',
                                    'example': 'JAWA TENGAH'
                                },
                                'city': {
                                    'type': 'string',
                                    'example': 'KAB. BANJARNEGARA'
                                },
                                'year': {
                                    'type': 'string',
                                    'example': '2022'
                                },
                                'latitude': {
                                    'type': 'string',
                                    'example': "7° 01' 35.61\" S"
                                },
                                'longitude': {
                                    'type': 'string',
                                    'example': "109° 35' 24.34\" E"
                                },
                                'hijri': {
                                    'type': 'string',
                                    'example': '1443'
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    404: {
        'description': 'Data not found',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'detail': {
                            'type': 'string',
                            'example': 'Imsyakiyah not found'
                        }
                    }
                }
            }
        }
    }
})
def read_imsyakiyah(stateId: int, cityId: int, year: str, date: Optional[str] = None):
   imsyakiyah = get_imsyakiyah(stateId, cityId, year, date)
   return imsyakiyah