# Suorituskyky — lue tämä ensin jos sivu pätkii

## Tärkein sääntö: pakota RTX päälle. Aina.

**Jos sivu pätkii, syy on lähes varmasti se, että selain piirtää integroidulla
näytönohjaimella eikä RTX:llä.**

Kone: Lenovo Legion, i9-13900HX + **NVIDIA GeForce RTX 4080 Laptop** + Intel UHD Graphics.

Ilman erillistä asetusta Windows ja NVIDIA valitsevat kortin **joka kerta uudestaan,
kun selaimen GPU-prosessi käynnistyy** — eivät kerran ja pysyvästi. Valintaan
vaikuttavat virrankäyttötila, verkkovirta/akku ja se, millä näytöllä ikkuna on.
Siksi *sama tiedosto* voi pyöriä sulavasti yhtenä päivänä ja tökkiä seuraavana
ilman että koodiin on koskettu.

### Näin tarkistat, kumpi kortti on käytössä

**Kortin nimi näkyy nyt aina** oikeassa alakulmassa: vihreällä = erillisnäytönohjain,
keltaisella = integroitu tai ohjelmistorasterointi. Hiiri päällä näyttää koko
tunnistemerkkijonon. Dev-tila ei siis enää ole tarpeen tähän.

- `NVIDIA GeForce RTX 4080` → kunnossa
- `Intel(R) UHD Graphics` → **tästä pätkiminen johtuu**

### Näin pakotat RTX:n (tehokkain ensin)

1. **Lenovo Vantage → Näytönohjain → dGPU / erillinen (MUX)**
   Vahvin: näyttö kytketään suoraan 4080:aan, jolloin valintaa ei enää tehdä.
   Vaatii uudelleenkäynnistyksen.
2. **Asetukset → Järjestelmä → Näyttö → Grafiikka** → lisää `chrome.exe` →
   Asetukset → **Suuri suorituskyky**. Sulje Chrome kokonaan (kaikki prosessit
   Tehtävienhallinnasta) ja avaa uudelleen.
3. **NVIDIA Ohjauspaneeli → Hallitse 3D-asetuksia → Ohjelma-asetukset** → Chrome
   → suuritehoinen NVIDIA-suoritin.

### Mikä EI toimi (testattu, älä tuhlaa aikaa)

- **`powerPreference: 'high-performance'` sivulla.** Se on koodissa ja on oikein
  pyytää, mutta ei riitä: Chromium valitsee kortin kerran GPU-prosessin
  käynnistyessä ja jakaa sen kaikille välilehdille. Sivu ei voi siirtää jo
  käynnissä olevaa prosessia.
- **`--force_high_performance_gpu`.** Kokeiltu omalla profiililla, jolloin syntyy
  oma GPU-prosessi joka lukee lipun — ja se päätyi silti Inteliin.

### Asetus on **sovelluskohtainen**

Chromelle tehty asetus ei koske muita selainmoottoreita. Esimerkiksi Claude-
työpöytäsovellus sisältää oman Chromiuminsa ja valitsee korttinsa itse. Se on
MSIX-paketoitu, joten se ei löydy `.exe`-tiedostoa selaamalla:

> Asetukset → Järjestelmä → Näyttö → Grafiikka → **Lisää sovellus** → vaihda
> pudotusvalikko **Microsoft Store -sovellus** → valitse sovellus → Asetukset →
> **Suuri suorituskyky**.

Asetus astuu voimaan vasta kun sovellus käynnistetään **kokonaan uudelleen** —
Chromium valitsee kortin GPU-prosessin käynnistyessä, joten jo ajossa olevaa
prosessia ei voi siirtää. Tämä on todennettu: sama sovellus näytti Inteliä ennen
uudelleenkäynnistystä ja RTX 4080:aa sen jälkeen.

## Toinen syy: Legion-virrankäyttötila

**Fn+Q** kiertää tiloja Quiet / Balance / **Performance**. *Balance*-tilassa
laiteohjelmisto kuristaa paketin, ja integroitu näytönohjain ottaa tehonsa samasta
budjetista → sama koodi hidastuu selvästi.

Oire josta tunnistat: **funktionäppäimet alkavat käyttäytyä oudosti** samaan aikaan
kun sivu hidastuu. Sama Fn+Q teki molemmat.

**Ennen esitystä: varmista Performance-tila ja verkkovirta.**

## Nopea tarkistus ennen esitystä

Avaa ⚙️ → **Dev** ja katso oikeaa yläkulmaa:

```
60 fps · cpu 4.5 ms
arv 2.2 · pii 1.7
NVIDIA GeForce RTX 4080
```

- `cpu` noin 4 ms → kunnossa
- `cpu` lähempänä 8 ms → kone on kuristettu, tarkista virrankäyttötila
- Kortin nimi `Intel` → pakota RTX yllä olevilla ohjeilla

`arv` = Babylon käy läpi kaikki meshit, `pii` = piirtokutsujen lähetys.
Jos `cpu` on paljon suurempi kuin `arv + pii`, aika menee omiin per-frame
-rutiineihin.

## Jos kone on vieras eikä sitä voi säätää

- **Hiukkaset**-nappi (⚙️-valikossa) pudottaa kaikki vapaat molekyylit —
  105 000 instanssia yhdellä klikkauksella.
- **Kalvo**-nappi piilottaa lipidikalvon, joka on raskain yksittäinen asia.
- Resoluutio laskee automaattisesti alle 45 fps:n, joten hidas kone
  heikkenee itsestään sen sijaan että jäisi jumiin.

## Muuta huomionarvoista

- Älä pidä montaa välilehteä sivusta auki. Jokainen varaa oman WebGL-kontekstin
  koko skenelle, ja selain alkaa lopulta hylätä vanhimpia — jolloin näkymä
  mustuu ilman virheilmoitusta.
- Älä pidä kehittäjätyökaluja auki mitatessasi. Firefoxissa se pudotti
  saman skenen 60 fps:stä 14,6 fps:ään.
- Chrome on tällä koneella mitattuna noin kaksi kertaa nopeampi kuin Firefox
  samalla näytönohjaimella.
- Taustaohjelmat vievät kaistaa: integroidulla kortilla ei ole omaa muistia,
  vaan se jakaa keskusmuistin. OneDrive-synkronointi ja qbittorrent näkyvät.
