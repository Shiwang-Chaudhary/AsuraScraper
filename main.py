from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from itertools import chain
from PIL import Image
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor
import shutil
import threading
import requests
import time
import json
import os


def init_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_manga_name(driver, mangaUrl):
    print("GET MANGA NAME RUN")
    """Extract manga name from the page"""
    driver.get(mangaUrl)
    time.sleep(2)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("span",class_="text-xl font-bold")
    manga_name = title_tag.get_text(strip=True) if title_tag else "Unknown Manga"
    return manga_name

def get_chapters_links(mangaUrl, driver):
    print("GET CHAPTER LINKS RUN")
    driver.get(mangaUrl)
    time.sleep(3)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    chapters = soup.find_all("div",class_="pl-4 py-2 border rounded-md group w-full hover:bg-[#343434] cursor-pointer border-[#A2A2A2]/20 relative")
    links = []
    for c in chapters:
        a = (c.find("a")).get("href")
        links.append("https://asuracomic.net/series/" + a)
    links.reverse()
    return links

def get_chapter_images(link):
    print("GET CHAPTER IMAGES RUN")
    driver = init_driver()
    try:
        driver.get(link)
        time.sleep(5)
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        chapters = soup.find_all("img", class_="object-cover mx-auto")
        images = []
        for c in chapters:
            src = c.get("src")
            if src:
                if src.startswith("http"):
                    images.append(src)
                else:
                    images.append("https://asuracomic.net" + src)
        return images
    finally:
        driver.quit()


def download_images(url,name):
    try:
        r = requests.get(url)
        f = open(name,"wb")
        f.write(r.content)
        f.close()
        print(name)
    except Exception as e:
        print(f"⚠️ Error downloading {url}: {e}")

def convert_to_pdf(imageList, driver,url):
    print("CONVERTING PDF")
    pdfName = get_manga_name(driver,url).strip().replace(" ","_")
    pdf = FPDF(unit="pt")
    pdf.set_compression(True)
    page_width = 595  # A4 size in points
    for imagePath in imageList:
      try:
        # img = Image.open(imagePath)
        # temp = imagePath
        # img.save(temp+".jpg","JPEG",quality=75,optimize=True)
        # pdf.add_page()
        # pdf.image(temp+".jpg",0,0,page_width)
        # os.remove(temp+".jpg")
        img = Image.open(imagePath).convert("RGB")
        img_w, img_h = img.size  # in pixels

        # Assume 72 DPI for image, convert pixels to points (PDF units)
        dpi = img.info.get('dpi', (72, 72))[0]
        page_w = img_w * 72.0 / dpi
        page_h = img_h * 72.0 / dpi
        if not imagePath.lower().endswith(".jpg"):
            imagePath += ".jpg"
        img.save(imagePath,"JPEG",quality=75,optimize=True)
        pdf.add_page(format=(page_w, page_h))
        pdf.image(imagePath, x=0, y=0, w=page_w, h=page_h)

      except Exception as e:
            print(f"⚠️ Skipping {imagePath}: {e}")
    pdfPath = os.path.join(os.path.dirname(os.getcwd()),f"{pdfName}.pdf")
    pdf.output(pdfPath,"F")
    print(f"PDF saved as {pdfPath}")


if __name__ == "__main__":
    # mangaUrl = "https://asuracomic.net/series/the-divine-demons-grand-ascension-202ed6aa"
    # mangaUrl = "https://asuracomic.net/series/surviving-as-a-genius-on-borrowed-time-1e809ee8"
    mangaUrl = "https://asuracomic.net/series/the-tang-clan-chronicles-24c76915"
    # mangaUrl = "https://asuracomic.net/series/reborn-on-the-demonic-cult-battlefield-caedcea5"
    # mangaUrl = "https://asuracomic.net/series/eternally-regressing-knight-644a62ec"
    # mangaUrl = "https://asuracomic.net/series/the-divine-demons-grand-ascension-945beb57"
    # mangaUrl = "https://asuracomic.net/series/reborn-on-the-demonic-cult-battlefield-67eabcc7"
    driver = init_driver()

    try:
        all_manga = {}
        allChapters = {}
        # 1️⃣ Get Manga Name
        manga_name = get_manga_name(driver, mangaUrl)
        print(f"Manga: {manga_name}")
        # 2️⃣ Get all chapter links
        chapters_links = get_chapters_links(mangaUrl, driver)
        print(f"Found {len(chapters_links)} chapters")

        # 3️⃣ Loop through chapters and build allChapters dict
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {executor.submit(get_chapter_images, link): index for index, link in enumerate(chapters_links)}
            for index,future in enumerate(future_to_index):
                try:
                    chapter_images = future.result()
                    chapter_name = f"Chapter {index + 1}"
                    allChapters[chapter_name] = chapter_images
                    print(f"✅ Stored {chapter_name} ({len(chapter_images)} images)")
                except Exception as e:
                    print(f"⚠️ Error processing chapter {index + 1}: {e}")
        # for index, link in enumerate(chapters_links):
        #     chapter_images = get_chapter_images(driver, link)
        #     chapter_name = f"Chapter {index + 1}"
        #     allChapters[chapter_name] = chapter_images
        #     print(f"✅ Stored {chapter_name} ({len(chapter_images)} images)")
        # 4️⃣ Store allChapters in all_manga under the manga name
        all_manga[manga_name] = {"allChapters": allChapters}

        # 5️⃣ Print final data
        print("\nFinal Map:")
        print(json.dumps(all_manga, indent=4))

        links = (allChapters).values()
        linksList = list(links) #Iteration m thi isliye list m convert krna pda
        requiredLinksList = list(chain.from_iterable(linksList)) #combine krne k liye saare links ko single list m
        print(f"total imagesLink : {len(requiredLinksList)}")
        print(f"Required links : {requiredLinksList}")

        if not os.path.exists("Images"):
            os.mkdir("Images")
        print("os.getcwd() before T1: ",os.getcwd())
        os.chdir(os.path.join(os.getcwd(),"Images"))    
        t1 = time.time()
        threads = []
        imageList = []
        # for index,l in enumerate(requiredLinksList):
        #     temp = threading.Thread(target=download_images,args=[l,f"{index+1}.jpg"])
        #     temp.start()
        #     threads.append(temp)

        # for thread in threads:
        #     thread.join()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for index, l in enumerate(requiredLinksList):
                img_path = os.path.join(os.getcwd(), f"{index+1}.jpg")
                imageList.append(img_path)
                futures.append(executor.submit(download_images, l, f"{index+1}.jpg"))

    # Wait for all downloads to complete
        for future in futures:
            future.result()

        # with ThreadPoolExecutor(max_workers=20) as executor:
        #     for index, l in enumerate(requiredLinksList):
        #         img_path = os.path.join(os.getcwd(), f"{index+1}.jpg")
        #         imageList.append(img_path)
        #         executor.submit(download_images, l, f"{index+1}.jpg")
        t2 = time.time()

        print("Time takes : ",t2-t1)
        # for i in range(len(requiredLinksList)):
        #     imgpath = os.path.join(os.getcwd(), f"{i+1}.jpg")

        #     imageList.append(imgpath)

        print("All image paths:", imageList)

        convert_to_pdf(imageList,driver,mangaUrl)
        # 🧹 Delete the Images folder after PDF creation
        try:
            os.chdir("..")  # Move out of the Images folder before deleting
            shutil.rmtree("Images")
            print("🗑️ Deleted 'Images' folder after PDF creation.")
        except Exception as e:
            print(f"⚠️ Could not delete Images folder: {e}")




    finally:
        driver.quit()

    

