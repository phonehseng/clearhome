# Clear House explainer: voiceover script

Long form, 16:9, 6:14.1 total. Narrator: calm, warm British professor. Read each line when its start time comes up;
the silent player shows the same line as a subtitle, so you can read along while recording.

## Intro

**Scene 1 · 10 PM, BLACKSBURG · “Nowhere to sleep tonight”** (0:00.0–0:16.5)

- `0:00.7` It's ten at night in Blacksburg, and someone has just realised they have nowhere safe to sleep.
- `0:06.4` Searching dozens of websites is the last thing they should have to do right now.
- `0:10.9` Today, we'll see how Clear House turns that search into one clear next step.

**Scene 2 · TODAY'S CLASS · “How Clear House works”** (0:16.5–0:30.1)

- `0:17.2` Here's our question for today: how can one website find real housing help, fast, without making things up?
- `0:24.8` We'll go in five steps, from the problem itself to the AI that answers.

## The problem

**Scene 3 · CHAPTER 1 · “What cost burdened means”** (0:30.1–0:48.0)

- `0:30.8` Housing experts call a household cost burdened when housing takes more than thirty percent of its income.
- `0:37.1` Pay fifteen hundred dollars in rent on four thousand a month, and that's already thirty-seven and a half percent.
- `0:43.7` When money is that tight, every wrong step costs more.

**Scene 4 · THE PROBLEM · “Help is scattered”** (0:48.0–1:07.0)

- `0:48.7` Shelters, rent help and affordable homes live on many different county, city and provider websites.
- `0:55.4` Some waitlists are closed, some listings are out of date, and scams target people in a hurry.
- `1:01.5` Clear House puts the checked options in one place, with the next step spelled out.

**Scene 5 · MOST PEOPLE THINK · “Can't I just walk in?”** (1:07.0–1:23.7)

- `1:07.7` Most people think a shelter is somewhere you simply walk into.
- `1:11.6` But many Northern Virginia shelters start with a call to an intake or referral line, which screens you and finds a bed.
- `1:18.5` So the most useful thing we can show is exactly who to call, and when.

## Checked data

**Scene 6 · CHAPTER 2 · “Every record checked by hand”** (1:23.7–1:43.8)

- `1:24.4` Underneath everything is a list of four hundred and nine resources, each checked against an official page.
- `1:30.8` That's three hundred and nine homes and floor plans, thirty-three emergency shelters and thirty-one help programs.
- `1:38.1` They cover two regions: Northern Virginia, and Blacksburg near Virginia Tech.

**Scene 7 · HOW A RECORD IS MADE · “From official page to listing”** (1:43.8–2:03.7)

- `1:44.5` Each record starts on an official provider or government page, never a search summary.
- `1:50.1` Phone numbers, addresses and rents are copied exactly, and anything unpublished is marked unknown, not guessed.
- `1:57.4` Every link says where it really goes, and every listing gets a date when it must be checked again.

**Scene 8 · WHY DATES MATTER · “Listings expire on purpose”** (2:03.7–2:20.1)

- `2:04.4` A listing that was true last month can quietly stop being true.
- `2:08.6` So homes drop out of search when their review date passes, about a week after they were checked.
- `2:14.5` Shelters never disappear for that reason; they simply go back to call to confirm.

**Scene 9 · QUICK CHECK · “What does a county list prove?”** (2:20.1–2:34.4)

- `2:20.8` Quick check: if a home appears on a county list, what does that actually prove?
- `2:25.9` Think about it.
- `2:27.3` It proves the program is real and official, not that a unit is free today, so we say call to confirm.

## Finding a home

**Scene 10 · CHAPTER 3 · “Search the way you live”** (2:34.4–2:46.3)

- `2:35.1` People don't think in counties; they think about work, school and the bus home.
- `2:40.4` So you can simply type: a place near my office at eighteen hundred Tysons Boulevard.

**Scene 11 · NO AI NEEDED · “Near my office, in seconds”** (2:46.3–3:04.3)

- `2:47.0` A small script reads the place out of your sentence, and Google Places finds it on the map.
- `2:52.7` Checked homes are ranked by distance, and Google Routes adds real drive and transit times.
- `2:58.7` That whole answer arrives almost instantly, because it doesn't need an AI to guess.

**Scene 12 · A REAL EXAMPLE · “Closest homes to Reston Town Center”** (3:04.3–3:16.5)

- `3:05.0` Here's a real answer from our tests for homes near Reston Town Center.
- `3:09.4` The closest checked home is three tenths of a mile away, about three minutes by car and seven by transit.

**Scene 13 · THE MAP · “A map that follows you”** (3:16.5–3:28.6)

- `3:17.2` The map works like a friend pointing at the right street while you talk.
- `3:21.3` When an answer names five homes, or you pick a neighbourhood like Reston, the map moves to show exactly those.

## Gemma 4 on Google Cloud

**Scene 14 · CHAPTER 4 · “Meet Gemma 4”** (3:28.6–3:43.6)

- `3:29.3` For open questions, like how to qualify for a voucher, Clear House uses Gemma 4, Google's open model.
- `3:37.0` Specifically the twenty-six billion parameter version, and every answer says which model wrote it.

**Scene 15 · KEY IDEA · “Grounding”** (3:43.6–3:55.7)

- `3:44.3` The key idea is grounding: the AI may only answer from facts we hand it.
- `3:49.1` A script picks the dozen or so checked records that match your question, and Gemma writes from those alone.

**Scene 16 · THE PIPELINE · “From question to answer”** (3:55.7–4:08.8)

- `3:56.4` Your question goes in, and the matching records are ranked so the most useful ones come first.
- `4:02.3` Gemma's answer streams in word by word, and a script turns every named place into a linked card.

**Scene 17 · THE SPEED PROBLEM · “Thinking took over a minute”** (4:08.8–4:24.8)

- `4:09.5` On the hosted API, Gemma spent about seventy-two seconds reasoning before writing a single word.
- `4:15.8` That's far too long for someone looking for shelter tonight.
- `4:19.5` On our own GPU, the first words arrive in about three seconds.

**Scene 18 · HOW WE FIXED IT · “Our own Gemma on Google Cloud”** (4:24.8–4:45.4)

- `4:25.5` So we run the very same Gemma 4 model ourselves, on a Cloud Run service with an NVIDIA L4 GPU.
- `4:32.7` We switch off the long reasoning step, and the GPU sleeps when nobody is using it.
- `4:38.1` If it's asleep or busy, the site quietly falls back to the Gemini API, so the chat never breaks.

**Scene 19 · THE GOOGLE STACK · “Every piece has a job”** (4:45.4–4:59.8)

- `4:46.1` Gemma writes the answers, Cloud Run hosts the site and the GPU, and Google Maps finds places and commute times.
- `4:54.0` Cloud Build packages every release, and Secret Manager keeps the keys out of the code.

## Safe and honest AI

**Scene 20 · CHAPTER 5 · “Safety comes first”** (4:59.8–5:13.3)

- `5:00.5` In an emergency, every page leads with nine one one and two one one, before any AI answer.
- `5:06.7` And Clear House never claims a bed is free; shelters always say call to confirm a bed tonight.

**Scene 21 · PRIVACY · “Collect only what we need”** (5:13.3–5:31.5)

- `5:14.0` There are no accounts, and Social Security and account numbers are removed before any text reaches the AI.
- `5:20.6` If you tap Near me, your location is rounded to about a hundred metres and never stored.
- `5:25.9` Domestic violence shelters never show an address, only the hotline to call.

**Scene 22 · HONEST BY DESIGN · “When rent isn't published”** (5:31.5–5:44.8)

- `5:32.2` Many homes don't publish their rent, and a chatbot could easily invent one.
- `5:37.0` Instead, Clear House shows a clearly labeled estimate from similar checked homes nearby, and tells you to ask the provider.

**Scene 23 · QUICK CHECK · “If the AI can't answer”** (5:44.8–5:58.0)

- `5:45.5` Last check: what happens if Gemma can't answer in time?
- `5:49.5` Think about it.
- `5:50.9` The chat still lists the checked resources that match, with phone numbers, so nobody is left with nothing.

## Recap

**Scene 24 · RECAP · “What you can now explain”** (5:58.0–6:14.1)

- `5:58.7` So: four hundred and nine checked resources, maps that think like you, and Gemma 4 answering in seconds on Google Cloud.
- `6:06.9` All of it grounded, private and honest about what it doesn't know.
- `6:10.9` A clearer path to a place to call home.
