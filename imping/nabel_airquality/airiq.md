# Replace the API-Key YOUR_KEY by your key
curl 'https://api.airvisual.com/v2/current?city=Amsterdam&state=Noord‑Holland&country=Netherlands&key=YOUR_KEY'
curl --location -g 'http://api.airvisual.com/v2/countries?key=YOUR_KEY'

curl --location -g 'http://api.airvisual.com/v2/city?city=Los%20Angeles&state=California&country=USA&key=YOUR_KEY'

curl "https://api.airvisual.com/v2/current?city=Zurich&state=Zurich&country=Switzerland&key=YOUR_KEY"

curl "https://api.waqi.info/feed/zurich/?token=YOUR_TOKEN"
