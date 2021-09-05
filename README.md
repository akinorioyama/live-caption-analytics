# live-caption-analytics
This chrome extension sends captions to servers to perform analytics and return feedback to the sender. Thanks to the author of [google-meet-transcripts](https://github.com/dzaman/google-meet-transcripts), the extension reads live caption in Google Meet.

The <b>chrome extension</b> will post the data to two of your servers to analyze or record live transcript. The one endpoint is to perform caption <b>analysis</b> and the other is to send the latest lines of caption to <b>record</b> in a storage, in the sample, a Google spreadsheet. Those two endpoints are independent from each other and can be called separately. This [YouTube video](https://www.youtube.com/watch?v=g1aYP5yyyJQ) will show the screen interaction in the browser. Updated behaviors are included in [YouTube video](https://www.youtube.com/watch?v=TAUHOKM8Tug) (Aug. 30, 2021).

**Building blocks**
---
`live-caption-analytics` has three building blocks listed below. 

***1) chrome extension*** part captures live caption and send (request) the portion to servers configured in option settings for the extension, and then receive (response) and render the response from the server. The extension is publicly available from [here](https://chrome.google.com/webstore/detail/pppkdkcchlonlocoiejjinmkdncfblji).

***2) analysis*** receives the caption data from the extension and will perform due calculations to return the response to the sender. The extension users can configure three options and can interact with the UI to control the POST requests to the endpoints, which are `/`, `/log`, `/show`, `/notification` and `/caption`.

***3) record*** sends the current caption line to a POST endpoint. The endpoint can be a Google spreadsheet as in the sample `receive_data.gs` in the folder `peripheral_functions/Google spreadsheet`. The POST enabled spreadsheet will update the received data to the dedicated sheet.

Each section is stored in the following paths.
```
src              <-- 1) chrome extension
main.py          <---2) analysis - sample implementation
receive_data.gs  <-- 3) record - snippet to publish and will listen to POST calls
vocab_suggest.py <---4) analysis - sample implementation for vocabulary profile
                                   and for vocabulary suggestion
save_to_storage.py <---5) analysis - sample implementation for retriving stored caption
```
**Installation**
---
***1) chrome extension*** can be added via <i>"Add to Chrome"</i> from [here](https://chrome.google.com/webstore/detail/pppkdkcchlonlocoiejjinmkdncfblji) or via <i>Load unpackaged extension</i> from `chrome://extensions` by loading it from the folder `src`.

***2) analysis*** will start to listen simply by executing the main.py. Supply host and port in the argument. Configure the destination in the extention option `Server URL to record captions`. Running the script will create a sqllite database under the filename of `test.db`. Execute `vocab_suggest.py` once to add tables and download nltk.

***3) record*** will receive caption once a Google spreadsheet has the sample `receive_data.gs` in a file and doPost is set up as a site in `deploy`. Configure the destination in the extention option `Server URL to record for Google Spreadsheet`.

**Documentation**
---
User documentation for the extension will be updated in `doc` folder.

**Features**
---
Aside from the ***chrome extensions*** and key functions in ***analysis*** and ***record***, sample features for ***analysis*** are provided and listed below.

***1) synonym suggestion*** shows you synonyms of your spoken words.

***2) word frequency*** shows how often you use individual words.

***3) fluency*** shows how fluent you are in a-few-seconds segments. One to a few seconds chunk will be shown in each line.

***4) turn taking*** shows how much each speaker speaks among others.

***5) caption retrieval*** shows lines of captions interlaced with highlighted points through `/log` POST requests.

**(In pipeline)**

Candidate 1: ***target vocabulary*** will show the target language for a single session or cross sessions. Checkboxes will be ticked once a word is used in the session. This may use SRS from apps.
- [x] Show list of words to cover (arbitrary option string to define the target words)
- [ ] Store the target words for each session
- [ ] Create a list of words for session through context analysis


**References**
---
***1) vocabulary profile*** CEFR-J Wordlist is used in the program and included in this repo.

The CEFR-J Wordlist Version 1.5. Compiled by Yukio Tono, Tokyo University of Foreign Studies. Retrieved from https://www.cefr-j.org/data/CEFRJ_wordlist_ver1.5.zip on 25/08/2020.

[Octanove Vocabulary Profile C1/C2 (ver 1.0)](https://github.com/openlanguageprofiles/olp-en-cefrj/blob/master/octanove-vocabulary-profile-c1c2-1.0.csv) — vocabulary list annotated with CEFR-J levels (for C1/C2 levels), created by [Octanove Labs](http://www.octanove.com/). Retrieved on 04/08/2021

**Changes**
---
Below are major changes.

|Date|Version|Changes|
|---|---|---|
|20210905|v1.0.1|<b>Options</b>: arbitrary option string in chrome extension option to configure what to show.<br><b>Usability</b>: always show extension screen buttons|
|20210827|v1|<b>Released</b>|