from HTMLParser import HTMLParser, HTMLParseError
from htmlentitydefs import name2codepoint
from BeautifulSoup import BeautifulSoup 
import datetime
import sys
import os
import re

try:
    # For Python 3.0 and later
    from urllib.request import urlopen
    import urllib
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen
    import urllib2
    
try: 
    import dryscrape
except ImportError:
    Log("Can't continue, need the dryscrape module to continue")


TGC_COURSE_URL = 'http://www.thegreatcourses.com/courses/'
TGC_SEARCH_URL = 'http://www.thegreatcourses.com/search/?q='
USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0'
ONE_DAY = datetime.timedelta(days=1)
TODAY = datetime.date.today()

# For Sure yo

def Start():

    HTTP.CacheTime = CACHE_1DAY
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.54'
    HTTP.Headers['Accept-Language'] = 'en-us'
    
class TGCAgent(Agent.TV_Shows):
    
    name = 'TGC'
    languages = [Locale.Language.English]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    class MyDESCParser(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.recording = 0
            self.data = []

        def handle_starttag(self, tag, attributes):
            if tag != 'div':
                return
            if self.recording:
                self.recording = self.recording + 1
                return
            for name, value in attributes:
                if name == 'class' and value == 'course-description':
                    break
            else:
                return
            self.recording = 1

        def handle_endtag(self, tag):
            if tag == 'div' and self.recording:
                self.recording = self.recording - 1

        def handle_data(self, data):
            if self.recording:
                self.data.append(data)
    
    class MyLTITLEParser(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.recording = 0
            self.data = []
            self.newdata = 0
            self.c = ''
            self.c2 = ''
            self.newdata2 = []
            self.switch = 0

        def handle_starttag(self, tag, attributes):
            if tag != 'div':
                return
            if self.recording:
                self.recording = self.recording + 1
                return
            for name, value in attributes:
                if name == 'class' and value == 'lecture-title':
                    self.switch = 0
                    break
            else:
                return
            self.recording = 1

        def handle_endtag(self, tag):
            if tag == 'div' and self.recording:
                self.recording = self.recording - 1

        def handle_data(self, data):
            if self.recording:
                if data and data != 'x' and data != ' ':
                    if self.switch == 1:
                        last = self.data.pop()
                        self.newdata = ' '. join([last, data])
                        self.data.append(self.newdata)
                        self.switch = 0
                    else:
                        self.data.append(data)

        def handle_entityref(self, ref):
            # called for each entity reference, e.g. for "&copy;", ref will be "copy"
            if ref in ('lt', 'gt', 'quot', 'amp', 'apos'):
                text = '&%s;' % ref
            else:
                # entity resolution graciously donated by Aaron Swartz
                def name2cp(k):
                    import htmlentitydefs
                    k = htmlentitydefs.entitydefs[k]
                    if k.startswith("&#") and k.endswith(";"):
                        return int(k[2:-1]) # not in latin-1
                    return ord(k)
                try: name2cp(ref)
                except KeyError: text = "&%s;" % ref
                else: text = unichr(name2cp(ref)).encode('utf-8')
            self.c = text
            if self.data and self.recording:
                last = self.data.pop()
                self.newdata = ' '.join([last,self.c])
                self.data.append(self.newdata)
                #print "Newdata:     ", self.newdata
                self.switch = 1

        def handle_charref(self, name):
            if name.startswith('x'):
                self.c2 = chr(int(name[1:], 16))
            else:
                try:
                    self.c2 = chr(int(name))
                except (TypeError, ValueError):
                    Log("unknown character")

            if self.data and self.recording:
                last = self.data.pop()
                self.newdata2 = ' '.join([last,self.c2])
                self.data.append(self.newdata2)
                self.switch = 1

    class MyLDESCParser(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.recording = 0
            self.data = []
            self.newdata = 0
            self.newdata2 = 0
            self.c = ''
            self.c2 = ''
            self.switch = 0

        def handle_starttag(self, tag, attributes):
            if tag == 'em' and self.recording:
                self.switch = 1
            if tag != 'div':
                return
            if self.recording:
                self.recording = self.recording + 1
                return
            for name, value in attributes:
                if name == 'class' and value == 'lecture-description-block left' or value == 'lecture-description-block right':
                    break
            else:
                return
            self.recording = 1

        def handle_endtag(self, tag):
            if tag == 'a' and self.recording:
                self.recording = self.recording - 1
            elif tag == 'em' and self.recording:
                self.switch = 1

        def handle_data(self, data):
            if self.recording:
                if data and data != 'x' and data != ' ':
                    if self.switch == 1:
                        last = self.data.pop()
                        self.newdata = ' '. join([last, data])
                        self.data.append(self.newdata)
                        self.switch = 0
                    else:
                        data.strip()
                        self.data.append(data)


        def handle_entityref(self, ref):
            # called for each entity reference, e.g. for "&copy;", ref will be "copy"
            if ref in ('lt', 'gt', 'quot', 'amp', 'apos'):
                text = '&%s;' % ref
            else:
                # entity resolution graciously donated by Aaron Swartz
                def name2cp(k):
                    import htmlentitydefs
                    k = htmlentitydefs.entitydefs[k]
                    if k.startswith("&#") and k.endswith(";"):
                        return int(k[2:-1]) # not in latin-1
                    return ord(k)
                try: name2cp(ref)
                except KeyError: text = "&%s;" % ref
                else: text = unichr(name2cp(ref)).encode('utf-8')
            self.c = text
            if self.data and self.recording:
                last = self.data.pop()
                self.newdata = ' '.join([last,self.c])
                self.data.append(self.newdata)
                #print "Newdata:     ", self.newdata
                self.switch = 1


        def handle_charref(self, name):
            if name.startswith('x'):
                self.c2 = chr(int(name[1:], 16))
            else:
                try:
                    self.c2 = chr(int(name))
                except (TypeError, ValueError):
                    Log("unknown character")    
            if self.data and self.recording:
                last = self.data.pop()
                self.newdata2 = ' '.join([last,self.c2])
                self.data.append(self.newdata2)
                self.switch = 1

    class MyLecturerParser(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.recording = 0
            self.data = []

        def handle_starttag(self, tag, attributes):
            if tag != 'span':
                return
            if self.recording:
                self.recording = self.recording + 1
                return
            for name, value in attributes:
                if name == 'class' and value == 'name':
                    break
            else:
                return
            self.recording = 1

        def handle_endtag(self, tag):
            if tag == 'span' and self.recording:
                self.recording = self.recording - 1

        def handle_data(self, data):
            if self.recording:
                self.data.append(data.strip())
    
    def getRating(self, html):
        soup = BeautifulSoup(html)
        rHTML = soup.find(itemprop='ratingValue')
        rating = rHTML.getText()
        return float(rating)
    
    def getDESC(self, html):
        DESC = ''
        
#        request = urllib2.Request(courseURL)
#        request.add_header('User-Agent', USER_AGENT)
#        opener = urllib2.build_opener()
#        html = opener.open(request).read()
        parser = self.MyDESCParser()
        parser.feed(html)
        data = parser.data
        
        for desc in data:
            if desc == "Hide Full Description":
                break
            elif desc == "Please Verify Account to Continue":
                break
            if desc.isspace():
                DESC = "\n".join([DESC,desc])
            else:
                DESC = ''.join([DESC,desc])
        
        return DESC.strip()
    
    def SearchCourse(self, mdatashow, cNum):
        course = mdatashow
        fixCourse = course
        CN = 31337

        sResults = { }
        sResultsSPAN = [ ]
        spanLen = [ ]
        sTitleResults = [ ]
        
        
        mdatashow = mdatashow.replace(':', '%3A')
        mdatashow = mdatashow.replace('?', '%3F')
        mdatashow = mdatashow.replace(',', '%2C')
        mdatashow = mdatashow.replace(' ', '+')
        
        course = course.replace(':', '')
        course = course.replace('"', '')
        course = course.replace(',', '')
        course = course.replace('?', '')
        course = course.replace(' ', '.*')
        course = course.replace('The', '')
        course = course.replace ('the', '')
        course = course.replace ('of', '')

        
        searchURL = ''.join([TGC_SEARCH_URL,mdatashow])
        request = urllib2.Request(searchURL)
        request.add_header('User-Agent', USER_AGENT)
        opener = urllib2.build_opener()
        html = opener.open(request).read()
        
        re_course = re.compile(course, re.DOTALL | re.IGNORECASE)
    
        soup = BeautifulSoup(html)
        sresult = soup.findAll(attrs={"class": "item-inner"})
        Log("Locating search results...")
        
        for link in sresult:
            title = link.a['title']
            Log("Title: %s" % link.a['title'])
            re_course_match = re_course.match(title)
            if re_course_match is not None:
                Log("Match found for: %s" % fixCourse)
                Log("Title found is: %s" % title)
                Log("Link is: %s" % link.a['href'])
                sResults.update({title: link.a['href']})
                sResultsSPAN.append(re_course_match.span())
                sTitleResults.append(title)
        
        Log("Finding best match...")
        for spanR in sResultsSPAN:
            spanLen.append(spanR[1] - spanR[0])
            Log("Span length for is: %s" % spanLen[-1])
            
        cindex = spanLen.index(max(spanLen))
        Results = {'title': sTitleResults[cindex], 'href': sResults[sTitleResults[cindex]]}
        #cindex = max(xrange(len(spanLen)), key=spanLen.__getitem__)
        #checking if there is a course number
        if cNum != 0:
            while (CN != cNum):

                Log("CourseTitle is: %s" % sTitleResults[cindex])
                Log("CourseURL is: %s" % sResults[sTitleResults[cindex]])

                resultsURL = sResults[sTitleResults[cindex]]
                request = urllib2.Request(resultsURL)
                request.add_header('User-Agent', USER_AGENT)
                opener = urllib2.build_opener()
                html = opener.open(request).read()
                soup = BeautifulSoup(html)
  
                #courseNum = soup.find("div", { "class" : "course-number" } )
                #CN = courseNum.getText().split(';',1)[-1]
                courseNum = soup.find("div", { "class" : "course-number" } )
                if courseNum is not None:
                    CN = courseNum.getText().split(';',1)[-1]
                else:
                    courseNum = soup.find("span", { "class" : "course-num" } )
                    CN = courseNum.getText().split('No.', 1)[-1]
                    CN = CN.split(';', 1)[-1].strip()
                Log("Course Number Search: %s" % cNum)
                Log("Course Number Found: %s" % CN)

                if cNum == CN:
                    Results = {'title': sTitleResults[cindex], 'href': sResults[sTitleResults[cindex]]}
                else:
                    del spanLen[cindex]
                    cindex = spanLen.index(max(spanLen))

                    
        return Results
            
    def search(self, results, media, lang, manual=False):
        id2 = media.show
        id2 = id2.replace("'", ' ')
        id2 = id2.replace('"', ' quot ')
        show = media.show.lower()
        show = show.replace(' ', '-')
        show = show.replace(':', '')
        show = show.replace(',', '')
        show = show.replace(' "', ' quot ')
        show = show.replace('" ', ' quot ')
        show = show.replace('?', '')
        show = show.replace("'", "-")
        Log("show value: %s" % show)
        courseURL = ''.join([TGC_COURSE_URL, show, '.html'])
        Log("Did the search")
        Log("CourseURL %s" % courseURL)  
        Log("Media name: %s" % media.name)  
        results.Append(
             MetadataSearchResult(
                id = id2,
                name = id2,
                year = 2017,
                score = 99,
                lang = lang
            )
        )
        Log("Added results")
    
            

    def update(self, metadata, media, lang):
        lecturers = []
        pNames = []
        pNamesURL = []
        lRoles = []

        Log("def update()")
        show = metadata.id
        mdatashow = show.replace('quot', '"')
        mdatashow = mdatashow.replace(' s ', "'s ")
        reCourse = re.search('TGC[0-9]{1,4}', mdatashow, re.IGNORECASE)
        if reCourse is not None:
            rg = re.compile("TGC", re.IGNORECASE)
            cNum = rg.split(mdatashow)[-1]
            #cNum = mdatashow.split('[',1)[-1]
            #cNum = cNum.replace(']','')
            #cNum = cNum.split('TGC',1)[-1]
            Log("Course Number: %s"  % cNum)
            metadata.title = rg.split(mdatashow)[0]
        else:
            metadata.title = mdatashow
            cNum = 0
        #metadata.title = mdatashow
        Log("metadata.title: %s" % metadata.title)
        show = metadata.title
        show = show.lower()
        show = show.replace(':', '')
        show = show.replace(',', '')
        show = show.replace('"', ' quot ')
        #show = show.replace('" ', ' quot ')
        show = show.replace('?', '')
        show = show.replace("'", "-")
        show = show.replace('  ', ' ')
        show = show.replace(' ', '-')
        courseURL = ''.join([TGC_COURSE_URL, show, '.html'])
        courseURL = courseURL.replace('-.html', '.html')
        Log("update() CourseURL: %s" % courseURL)
        Log("Calling dryscrape and visiting coursURL")
        #session = dryscrape.Session()
        #session.set_header('User-Agent', USER_AGENT)
        #session.visit(courseURL)
        #html = session.body()
        
        #Log("Getting Rating")
        #r = self.getRating(html)
        #rating = 2*r    
        
        Log("calling urllib2 and visiting coursURL")
        request = urllib2.Request(courseURL)
        request.add_header('User-Agent', USER_AGENT)
        opener = urllib2.build_opener()

        try:
            html = opener.open(request).read()
        except urllib2.HTTPError:
            Log("courseURL not found... Searching for related courses: %s" % metadata.title)
            Results = self.SearchCourse(metadata.title, cNum)
            Log("Course found, URL: %s" % Results['href'])
            scourseURL = Results['href']
            metadata.title = Results['title']
            request = urllib2.Request(scourseURL)
            request.add_header('User-Agent', USER_AGENT)
            opener = urllib2.build_opener()
            html = opener.open(request).read()
            

        data = self.getDESC(html)
        Log("Adding metadata summary")
        metadata.summary = data
        #Log("Retrieving episode/season number")
        #season_num = media.season
        #episode_num = media.episode
        Log("Calling MyLDESCParser()")
        parser = self.MyLDESCParser()
        Log("Calling MyLTITLEarser()")
        parser2 = self.MyLTITLEParser()
        Log("Calling MyLDESCParser().feed(html)")
        parser.feed(html)
        Log("Calling MyLTITLEarser().feed(html)")
        parser2.feed((html))
        Log("Calling MyLecturerParser()")
        parser3 = self.MyLecturerParser()
        Log("Calling MyLecturerParser().feed(html)")
        parser3.feed(html)
        if parser3.data:
            lecturer = str(parser3.data[0].strip())
            #lecturer = lecturer.replace(',', '')
            #lecturer = lecturer.replace('.', '') 
        else:
            lecturer = "me"
            Log("More than one professor, getting all lecturers...")
            soupPro = BeautifulSoup(html)
            professorNames = soupPro.findAll("div", { "class" : "professor-name"})
            for p in professorNames:
                lecturers.append(p.getText())
                Log("Professor: %s" % p.getText())
            firstBlock = soupPro.find("img", { "class" : "active" })
            pNames.append(firstBlock['alt'])
            pNamesURL.append(firstBlock['src'])
            lRoles.append(str(lecturers[0].split(firstBlock['alt'],1)[-1]))
            lRoles[0] = lRoles[0].split(',',1)[-1].strip()
            metadata.roles.clear()
            meta_role = metadata.roles.new()
            meta_role.name = pNames[0]
            meta_role.role = lRoles[0]
            Log("meta_role.role: %s" % meta_role.role)
            meta_role.photo = pNamesURL[0]
            remBlocks = soupPro.findAll("img", { "class" : ""})
            COUNT=1
            for remaining in remBlocks:
                meta_role = metadata.roles.new()
                pNames.append(remaining['alt'])
                pNamesURL.append(remaining['src'])
                lRoles.append(str(lecturers[COUNT].split(remaining['alt'],1)[-1]))
                lRoles[COUNT] = lRoles[COUNT].split(',',1)[-1].strip()
                Log("Professor: %s  - Role: %s" % (pNames[COUNT], lRoles[COUNT]))
                meta_role.name = pNames[COUNT]
                #meta_role.role = lRoles[COUNT]
                Log("meta_role.role: %s" % meta_role.role)
                meta_role.photo = pNamesURL[COUNT]
                COUNT = COUNT + 1
         
        soup2 = BeautifulSoup(html)
        Log("Finding professor photo...")
        pBlock = soup2.find("div", { "class" : "prof-icon hide-below-768"})
        if pBlock is not None:
            pPhotoblock = pBlock['style']
            pPhotoURL = re.findall(r"'(.*?)'", pPhotoblock)
            for pURL in pPhotoURL:
                Log("Professor photo URL: %s" % pURL)
        else:
            pURL = None
            
        pNameBlock = soup2.find("img", { "class" : "active" })
        if pNameBlock is not None:
            pName = pNameBlock['alt']
        lrole = lecturer.split(pName,1)[0]
        if lecturer != "me":
            metadata.roles.clear()
            meta_role = metadata.roles.new()
            meta_role.name = pName
            meta_role.role = lrole
        eSummaryData = parser.data
        eTitleData = parser2.data
        Log("Updating episode data")
        @parallelize
        def UpdateEpisodes(html=html, eSummaryData=eSummaryData, eTitleData=eTitleData, lecturer=lecturer):
            Log("def UpdateEpisodes()")
            if media is not None:
                Log("Media is not None")
                for season_num in media.seasons:
                    Log("Season Number:%s" % season_num)
                    episodes = media.seasons[str(season_num)].episodes
                    Log("Episodes: %s" % episodes)
                    for episode_num in media.seasons[str(season_num)].episodes:
                        Log("Episode number:%s" % episode_num)
                        if int(episode_num) != 0:
                            episode = metadata.seasons[str(season_num)].episodes[str(episode_num)]
                            Log("Running UpdateEpisode...")
                            @task
                            def UpdateEpisode(episode=episode, html=html, episode_num=episode_num, eSummaryData=eSummaryData, eTitleData=eTitleData, lecturer=lecturer):
                                Log("def UpdateEpisode()")
                                lecture_len = len(eSummaryData)
                                lecture_len2 = len(eTitleData)
                                Log("Lecture array length: %s" % lecture_len)
                                if int(episode_num) <= lecture_len:
                                    Log("Episode Title: %s" % eTitleData[int(episode_num) - 1])
                                    Log("Episode summary %s" % eSummaryData[int(episode_num) - 1].strip())
                                    if episode.summary is None:
                                        episode.summary = str(eSummaryData[int(episode_num) - 1].strip())
                                    if episode.title is None:
                                        episode.title = str(eTitleData[int(episode_num) - 1 ])
                                    Log("episode.summary: %s" % episode.summary)
                                    Log("episode.title: %s" % episode.title)
                                    Log("Getting Lecturer")

                                Log("Lecturer: %s" % lecturer)
                                #episode.directors.clear()
                                #episode.writers.clear()
                                #episode.directors.add(lecturer)
                                #episode.writers.add(lecturer)
                                #Thanks to ZeroQI for the directors edit
                                episode.directors.clear()
                                meta_director = episode.directors.new()
                                COUNT=0
                                if lecturer == "me": 
                                    for pname in pNames:
                                        meta_director = episode.directors.new()
                                        meta_director.name = pname 
                                        meta_director.role = pname
                                        COUNT = COUNT + 1
                                else:
                                    meta_director.name = pName # role name
                                    meta_director.role = lrole # actor name
                                #meta_role.photo = None #url of actor photo
                                if pURL is not None:
                                    meta_director.photo = pURL #url of actor photo
                                    Log("meta_director.photo: %s" % meta_director.photo)
                                    meta_role.photo = pURL
                                    Log("meta_role.photo: %s" % meta_role.photo)
                                #Log("episode.directors: %s" % episode.directors)
                                #Log("episode.writers: %s" % episode.writers)
                                Log("Setting episode dates")    
                                if episode_num == 1:
                                    episode.originally_available_at = TODAY
                                    Log("For episode: %s the date is %s" % (episode_num, episode.originally_available_at))
                                else:
                                    tdelta = datetime.timedelta(days=int(episode_num))
                                    newDate = TODAY + tdelta
                                    episode.originally_available_at = newDate
                                    Log("For episode: %s the date is %s" % (episode_num, episode.originally_available_at))
                        else:
                            Log("I do not update episodes 0. No Information to retrieve.")    
                Log("getting Art images")
                    
                    
        #episode.rating = rating
        Log("Downloading Art")
        @parallelize
        def DownloadArt(html=html):
            Log("DownloadArt()")
            art = [ ]
            Art = { }
            soup = BeautifulSoup(html)
            for link in soup.findAll("a", "cloud-zoom-gallery lightbox-group"):
                art.append(link.get('href'))
            Art['fanart'] = art[0]
            Art['poster'] = art[1]
            Log("Fanart URL: %s" % Art['fanart'])
            Log("Poster URL: %s" % Art['poster'])
            if Art['poster'] not in metadata.posters:
                @task
                def DownloadPoster(poster_url=Art['poster']):
                    Log("Downloading posters")
                    try:
                        metadata.posters[poster_url] = Proxy.Preview(HTTP.Request(poster_url).content, sort_order=1)
                    except: 
                        Log("Download of poster image failed! - %s" % poster_url)
                        pass
            else:
                Log("Poster art already in metadata.posters")
            metadata.posters.validate_keys(Art['poster'])
            
            if Art['fanart'] not in metadata.art:
                @task
                def DownloadFanArt(fanart_url=Art['fanart']):
                    Log("Downloading fanart")
                    try:
                        metadata.art[fanart_url] = Proxy.Preview(HTTP.Request(fanart_url).content, sort_order=1)
                    except: 
                        Log("Download of fanart image failed! - %s" % fanart_url)
                        pass
            else:
                Log("Fanart already in metadata.art")                        
            metadata.art.validate_keys(Art['fanart'])
            
        Log("Done")    
        return