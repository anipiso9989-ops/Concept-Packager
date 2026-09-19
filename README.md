# Concept Packager

> Note:
> There are 2 versions of this file, both are available.
>   The first version, `concept_packager.py`, is the one that I built personally.
>   The second verion, `concept_packager2.py` is the vibe coded version that includes upgrades, according to some ideas that I had.

What is this project, anyways?

This is my attempt to create a simple harness that lets you input your notes (given that they're markdown files stored on your computer) and outputs a simpler version.

### Why does it exist? (skip this section if you just want to use the project)

So, I'm obsessed with this idea I developed: atomic-agentic knowledge.

Atomic knowledge is the simplest possible representation of knowledge; an atomic knowledge unit is a single concept, self contained.

Agentic knowledge is **actionable** knowledge; something that provides unique utility that no other piece of knowledge would provide, otherwise.

This project strips everything from your .md files except agentic knowledge, represented in an atomic format.

Now, I do concede that you could just upload your .md files to ChatGPT and paste in the prompt, but do you really want to do that repeatedly? There's also a file upload limit associated with it.

So, I built this harness that only requires the user to input one thing: the filepath of the .md file (btw, you can only send one file at a time; I haven't yet figured out a way to send batches). My project essentially makes this whole process of simplifying information way easier, in my opinion. You only have to do Steps 1 and 2 once; steps 3 and 4 are super fast to do.

This program works in this way:
1. Connects to OpenRouter and sends over the file along with the prompt, which is stored inside the python file
2. AI model processes both the prompt and the file, and outputs it back to you

***
### How to Use

1. download just one of the python files, depending on what you want.

3. Go to [openrouter.com](openrouter.com) and create an account if you have not done so, already. Get an API key from them, and then paste in the exact key into line 5 of the python file (so open up the file in VSCode or a text editor app, and then on line 5, paste in your key between the double quotes) Now, save the python file and close it.

3.Open up your terminal. If you're on Windows, it's called Powershell. For Mac, it's just terminal.

4. On both Windows and Mac, type `cd Folder`, where you replace "Folder" with the exact name of the folder that the python file is in.
Then, type `python concept_packager.py`. It'll ask you to type/paste in the filepath of the .md file you want to send. Paste it in, and you'll get your response. Note: on Mac, you need to type `python3 concept_packager.py`. Don't forget the "3".

Quit the program by pressing "q" on your keyboard.

***

## Contributions

I built this project by myself in a day, so the only contributor is me, for the original one.

The enhanced version was vibe coded with GPT 5.6 Sol.
