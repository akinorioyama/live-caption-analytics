# live-caption-analytics
This chrome extension sends captions to servers to perform analytics and return feedback to the sender. Thanks to the author of [google-meet-transcripts](https://github.com/dzaman/google-meet-transcripts), the extension is first created to read live caption in **Google Meet**, and evolved to capture subtitles in **Zoom** and **Chrome built-in speech recognition** generated transcript rendered in the proprietary area of the extension by this extension. 

The <b>chrome extension</b> will post the data to two of your servers to analyze or record live transcript. The one endpoint is to perform caption <b>analysis</b> and the other is to send the latest lines of caption to <b>record</b> in a storage, in the sample, a Google spreadsheet. Those two endpoints are independent from each other and can be called separately. This [YouTube video](https://www.youtube.com/watch?v=g1aYP5yyyJQ) will show the screen interaction in the browser. Updated behaviors are included in [YouTube video](https://www.youtube.com/watch?v=TAUHOKM8Tug) (Aug. 30, 2021) and **_YouTube clip for v1.0.3 (~~to be updated soon~~ [1](https://youtu.be/ze80wsKugek), [2](https://youtu.be/PT1dbg1NPA0), and [3](https://youtu.be/Fw1d2o4A3b0)  )_**. V1.0.3.2 introduces tentative code blocks to import texts and use them for vocab coverage ([here](https://www.youtube.com/watch?v=FrjfukiYkhs) ~~clip will be **available soon**~~). V1.0.3.3 has an updated features in prompt backend to inform learners about one's overused words (shown [here](https://www.youtube.com/watch?v=PRg8LIX81Uk)).

From the version 1.0.4, <b>users must authenticate through Google account</b> to prove their identity. The sample application reads your account information shown in the popup after you explicitly <b>"Sign in with Google"</b> to continue to the server, as the prompt popup shows "To continue, Google will share your name, email address, ... with Live caption analytics." OAuth must be configured for your servers. 

**Building blocks**
---
`live-caption-analytics` has three building blocks listed below. 

***1) chrome extension*** part captures live caption and send (request) the portion to servers configured in option settings for the extension, and then receive (response) and render the response from the server. The extension is publicly available from [here](https://chrome.google.com/webstore/detail/pppkdkcchlonlocoiejjinmkdncfblji).

***2) analysis*** receives the caption data from the extension and will perform due calculations to return the response to the sender. The extension users can configure three options and can interact with the UI to control the POST requests to the endpoints, which are `/`, `/log`, `/show`, `/notification`, `/caption`, (`/render_in_full`, `/prompt_check` from v1.0.3 and `/show_list`,`/get_vocab`, `/personalize_session` from v1.0.3.1.n, `/personalize_session_settings`). The associated sample sites at the server include `/lca/sample_speaking_session` and `/lca_status/sample_session_copy`.

***3) record*** sends the current caption line to a POST endpoint. The endpoint can be a Google spreadsheet as in the sample `receive_data.gs` in the folder `peripheral_functions/Google spreadsheet`. The POST enabled spreadsheet will update the received data to the dedicated sheet.

Each section is stored in the following paths.
```
/src             <-- 1) chrome extension
main.py          <---2) analysis - sample implementation
receive_data.gs  <-- 3) record - snippet to publish and will listen to POST calls
vocab_suggest.py <---4) analysis - sample implementation for vocabulary profile
                                   and for vocabulary suggestion
save_to_storage.py <---5) analysis - sample implementation for retriving stored caption
/template and /static
                   <---6) analysis - sample pages for Chrome built-in and independent window
```
**Installation**
---
***1) chrome extension*** can be added via <i>"Add to Chrome"</i> from [here](https://chrome.google.com/webstore/detail/pppkdkcchlonlocoiejjinmkdncfblji) or via <i>Load unpackaged extension</i> from `chrome://extensions` by loading it from the folder `src`.

***2) analysis*** will start to listen simply by executing the main.py. Supply host and port in the argument. Configure the destination in the extention option `Server URL to record captions`. Running the script will create a sqllite database under the filename of `test.db`. Execute `vocab_suggest.py` once to add tables and download nltk.

***3) record*** will receive caption once a Google spreadsheet has the sample `receive_data.gs` in a file and doPost is set up as a site in `deploy`. Configure the destination in the extention option `Server URL to record for Google Spreadsheet`.

**Documentation**
---
User documentation for the extension will be updated in `doc` folder of the repo and in the <i>Live caption analytics</i> section of my website ([here](https://akinorioyama.com/live-caption-analytics/)). 

**Features**
---
Aside from the ***chrome extensions*** and key functions in ***analysis*** and ***record***, sample features for ***analysis*** are provided and listed below.

***1) synonym suggestion*** shows you synonyms of your spoken words.

***2) word frequency*** shows how often you use individual words.

***3) fluency*** shows how fluent you are in a-few-seconds segments. One to a few seconds chunk will be shown in each line.

***4) turn taking*** shows how much each speaker speaks among others.

***5) caption retrieval*** shows lines of captions interlaced with highlighted points through `/log` POST requests.

***6) Independent window*** shows pseudo page that is mostly identical to the capturing page interposed by extension at a destination `/lca_status/sample_session_copy`

***7) Dump*** shows all the results from available functions `/render_in_full`

***8) Built-in recognition*** uses Chrome built-in speech recognition to feed the data into the server. This allows users to capture their utterance at any service tentatively restricted to three domains - localhost/lca, rarejob.com, and eikaiwa.dmm.com (at `/lca/sample_speaking_session`).

***9) Prompt*** shows a prompt to solicit inputs initiated from server side

***10) coverage*** shows the use of pre-selected word in a session (configured in `session_settings` table)

***11) retrieval*** shows the list of vocabulary at a site (_~~WIP~~: and reflect those into a DB table_).

***12) personalization*** allows the learners to configure the lists of vocabulary to avoid, rephrase, and cover in `/personalize_session_settings`.

***13) start page*** (`/`) allows users to start pages to change settings for the features above, previously covered only in links written for each function.

***14) list sessions*** shows the recorded sessions for the authenticated user (at `list_session`).

***15) calling functions*** configures the features to show for the authenticated user (at `/personalize_calling_function`).

***16) authenticate other users*** permit other users for the session of others through token or email address (in `/personalize_session_accept_authorization` and `/personalize_session_authorization`).

***17) drag elements*** configures the positions of screen elements through an icon.

**(In pipeline)**

Candidate 1: ***target vocabulary*** will show the target language for a single session or cross sessions. Checkboxes will be ticked once a word is used in the session. This may use SRS from apps.
- [x] Show list of words to cover (arbitrary option string to define the target words)
- [X] Store the target words for each session (available from v1.0.3)
- [ ] Create a list of words for session through context analysis of external site
- [ ] Extract and arrange word/phrase/content through integrated analysis of 
- WordNet, WordNet Domains
- General Service List
- English Vocabulary Profile
- English Grammar Profile (potential use of classifying EGP through regular expression proposed by CEFR-J Grammar Profile)
- Universal/Dewey Decimal Classification (available in WordNet Domains)
- _finally_ CEFR descriptor/competency/can do.  

Candidate 2: ***authentication or user management*** will enable user management in the sample server application. This may include other authentication providers such as Facebook. 
- [X] allow other users to access the session recorded by the owner of the session

Candidate 3: ***other voice interactions*** will enable users to capture other sites.
- [ ] interactions on specific sites (Twitter Spaces)
- [ ] interactions to capture through option settings


**References**
---
***1) vocabulary profile*** CEFR-J Wordlist is used in the program and included in this repo.

The CEFR-J Wordlist Version 1.5. Compiled by Yukio Tono, Tokyo University of Foreign Studies. Retrieved from https://www.cefr-j.org/data/CEFRJ_wordlist_ver1.5.zip on 25/08/2020.

[Octanove Vocabulary Profile C1/C2 (ver 1.0)](https://github.com/openlanguageprofiles/olp-en-cefrj/blob/master/octanove-vocabulary-profile-c1c2-1.0.csv) — vocabulary list annotated with CEFR-J levels (for C1/C2 levels), created by [Octanove Labs](http://www.octanove.com/). Retrieved on 04/08/2021

***2) New General Service List*** NGSL is used in the program and included in this repo.

The New General Service List 1.1. compiled by Browne, C., Culligan, B. & Phillips, J. Retrieved from http://www.newgeneralservicelist.org/s/NGSL-101-with-SFI.xlsx on 14/09/2020. Licensed under [CC-BY-SA](http://creativecommons.org/licenses/by-sa/4.0/).

**Changes**
---
Below are major changes.

| Date     | Version    | Changes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|----------|------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 20220812 | v1.0.4.3   | **Critical fix**: time transcription start time for Google Meet<br>**Usability**: drag screen elements, configure calling functions in menu.<br>**Authentication**: generate token or list email address to give access to other users.                                                                                                                                                                                                                                                                                                                                       |
| 20220706 | v1.0.4.2   | **Critical fix**: locate transcription area for Google Meet (failed to locate transcription area at some point)<br>                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 20211225 | v1.0.4.1   | **Usability**: provide Chrome built-in languages<br>**Authentication**: require explit permission consent to use Google speech to text                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 20211112 | v1.0.4.0-1 | **Minor fix**:stabilize retrieve site text                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 20211110 | v1.0.4.0   | **Authentication**: authenticate through Google account<br>**Usability**:add <i>Start page</i> to access features and <i>download</i> for caption and vocabulary frequency                                                                                                                                                                                                                                                                                                                                                                                                    |
| 20211005 | v1.0.3.5   | **Major fix**: extension not shown in Google Meet                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 20211001 | v1.0.3.4   | **Configuration**: place elements and apply changes immediately<br>**Domains**: add a part of *.net domains                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 20210928 | v1.0.3.3   | **Personalization**: change vocabulary to work on<br>**DB filename**: from test.db to main.db<br>minor fixes: refrain from focusing on participant list                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 20210923 | v1.0.3.2   | **Configuration**: change session id and text color                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 20210922 | v1.0.3.1.2 | **Coverage**: Vocab game                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 20210921 | v1.0.3.1.1 | **Retrieval**: Search candidates of words and write to DB<br>**NGSL**: as in-depth classification                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 20210919 | v1.0.3.1   | Minor fixes. Add element position option                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 20210918 | v1.0.3     | **Independent window**: pseudo page that replicates extension capture<br>**Dump**: show all the results from available functions<br>**Built-in recognition**: use Chrome built-in speech recognition<br>**Prompt**: show a prompt to solicit inputs initiated from server side<br>**Session_settings**: the table is added. Available keys for session are <li>`vocab_to_cover` and `phrase_to_cover`: value entries with the key will list the words and its use in the session.<br>**Get vocab from an external site**: (**TODO:** .py to be added - in the future commits) |
| 20210911 | v1.0.2     | **Zoom**: zoomification to capture transcript in zoom subtitle area powered by 3rd party services (test drive done with Otter.ai)                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 20210905 | v1.0.1     | <b>Options</b>: arbitrary option string in chrome extension option to configure what to show.<br><b>Usability</b>: always show extension screen buttons                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 20210827 | v1         | <b>Released</b>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |