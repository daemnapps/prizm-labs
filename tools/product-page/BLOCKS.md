# The blocks

The standard blocks of a product page, for any brand, any product and any customer type. Every product page is built from these blocks only, in the order its recipe gives. Each block names its job, the inputs it reads, the customer evidence that decides its words, its rules, its artwork slots and its pass/fail checks. Brand, product and customer specifics are inputs, never part of a block.

## Inputs

- **brand**: brands/<brand>/: identity and web tokens (colours, type, spacing, button), offers and guarantee, review app export, competitors.
- **product**: brands/<brand>/products/<product>/: facts, parts or ingredients, what is in the box, how it is used, how long it lasts, store title, variants and purchase options.
- **avatar**: brands/<brand>/core-avatars/<avatar>/: the customer type this page is written for, and that customer type's language rows. A page has one primary avatar.

Moves used when refining a page: keep, amplify, add, refine, rebuild, merge, cut.

## buy-area

### gallery

**Job:** Show the product, the product in use and a real result before the customer reads a word.

**Inputs:** product facts; product photos from the picture process; review photos and videos

**Evidence:** Share of reviews that carry customer photos or video.

**Rules:**

- The same slots on every product of the brand, in the same order: 1 the product alone, 2 in use, 3 a real customer result, 4 a close-up of the detail that matters, 5 what is in the box, 6 scale (in the hand, on the body, in the room).
- Slot 1 is always the product. Slot 3 is always a real customer photo, never generated.
- Thumbnails load with the page and a tap swaps at once.

**Artwork:** six slots per product

**Checks:**

- [ ] slot 1 is the product
- [ ] slot 3 is a customer photo with its review id
- [ ] no thumbnail loads blank
- [ ] same slot order on every product

### proof-line

**Job:** Prove other customers bought it and it worked, before the name.

**Inputs:** review app totals; results-timeline output

**Evidence:** How often reviews or other customers' results are given as the reason to buy.

**Rules:**

- One review total and one average for the whole store, the same number everywhere on the site.
- Stars in the brand's accent colour, readable on the page background.
- May add one timing fact from the results timeline.

**Artwork:** a row of real customer faces or avatars

**Checks:**

- [ ] the total matches the review app's published count
- [ ] the same number on every page
- [ ] stars pass contrast on the background

### title

**Job:** Name the product exactly as the store names it.

**Inputs:** store product title

**Evidence:** -

**Rules:**

- The store's product title, word for word, everywhere (menu, cards, page).
- One size on every product page; one or two lines at most.
- A bundle gets a three-to-five-word line under its name saying what is in it.

**Checks:**

- [ ] title equals the store title
- [ ] never three lines at phone width
- [ ] same size on every product

### who-for

**Job:** Tell the customer in one line that this is for their problem or goal.

**Inputs:** avatar language rows: problem and goal language

**Evidence:** The problems or goals customers say they bought it for, ranked by how often they say them.

**Rules:**

- One line under the proof line.
- Names the top problems or goals for this product in the customers' own words, most-said first.
- Describes the customer (type, age, situation) only when the avatar's data supports it.

**Checks:**

- [ ] every problem or goal named appears in the language rows with its id
- [ ] one line at desktop width

### hero-quote

**Job:** Let one customer state the result in their own words.

**Inputs:** reviews

**Evidence:** Reviews that name a time and a result.

**Rules:**

- One verified review, quoted exactly.
- Prefer a review that names both a time and a result.
- No reviewer line under it.

**Checks:**

- [ ] quote matches the review text exactly
- [ ] review id recorded

### outcome-chips

**Job:** Four results the customer gets, scannable in a second.

**Inputs:** avatar language rows; product facts

**Evidence:** What customers were trying to achieve; what they say other products failed at.

**Rules:**

- Exactly four chips, two columns on every screen size.
- Outcomes only. Specifications belong in the description.
- One icon style for all four.

**Artwork:** one icon per outcome, one drawn set

**Checks:**

- [ ] four chips
- [ ] no specification numbers in a chip
- [ ] each outcome traceable to a language row or product fact

### offer-box

**Job:** Let the customer choose, and know exactly what they get, when, and for how much.

**Inputs:** store variants and purchase options; brand offers

**Evidence:** Refund, cancellation and objection reasons about price and terms.

**Rules:**

- Each option: price, the compare-at price crossed out, one savings figure in one style.
- Each option names what ships, and for repeat deliveries what ships next, how often and at what price.
- The best-value option is preselected and flagged.
- Prices are read from the store, never typed.

**Checks:**

- [ ] on-screen price equals checkout price for every option
- [ ] repeat contents and interval on screen where repeat delivery is offered
- [ ] one savings style

### expectation-line

**Job:** Set how soon it works for this product, so the customer does not give up early.

**Inputs:** results-timeline output for this product

**Evidence:** This product's own reviews that state when it worked.

**Rules:**

- Per product, never one shared sentence.
- Names what customers notice first and when the main result arrives, with the timeline's numbers.

**Checks:**

- [ ] different on every product
- [ ] every number traceable to the timeline output

### buy-button

**Job:** One action, and the terms around it in plain words.

**Inputs:** store purchase options; brand web tokens (button)

**Evidence:** Same as offer-box.

**Rules:**

- One button look on the whole site, from the brand's tokens: one height, one type size, one hover, no movement.
- Under it, for repeat delivery: what repeats, how often, at what price, and how to skip or cancel.
- A one-time option shows its price next to it.

**Checks:**

- [ ] adds the chosen option to the cart
- [ ] the terms line names contents, interval and price where repeat delivery is offered

### arrival-timeline

**Job:** Show what arrives and what changes on the same dates, up to the guarantee.

**Inputs:** store purchase options; results-timeline output; brand guarantee

**Evidence:** Results timeline counts.

**Rules:**

- Dates: today, each repeat delivery (when offered), the guarantee day.
- On each date: what arrives, and what customers say had changed by then.
- Choosing one delivery removes the repeat steps and keeps the rest.

**Checks:**

- [ ] repeat steps disappear on one-time and return on repeat
- [ ] every 'changed by then' line traces to the timeline output

### objections

**Job:** Answer the two questions that stop the sale, right under the button.

**Inputs:** avatar language rows: questions and objections; results-timeline output; brand guarantee

**Evidence:** Questions customers say the site did not answer, ranked.

**Rules:**

- The two most-asked unanswered questions, open by default. Where the data agrees, these are 'Will it work for me?' and 'How long until I see it?'.
- Answers use review counts and the guarantee. No claim the brand does not hold.

**Checks:**

- [ ] two questions, open
- [ ] both are the top two in the ranked questions
- [ ] every number in an answer is sourced

## description

### description

**Job:** What it is, how it works, what the customer gets.

**Inputs:** product facts; avatar language rows: how it feels or performs, what they like

**Evidence:** How customers describe it after use; what they like most.

**Rules:**

- Capitalised headline, one paragraph, the sub-head 'WHAT YOU GET', bullets, one closing line.
- The paragraph: what it is, how it works, what the customer notices first, in customers' words.
- One bullet style. Each specification says what it does for the customer.
- Closing line: what is in the box and how long it lasts. One figure for each across the page.

**Checks:**

- [ ] five parts in this order
- [ ] one bullet style
- [ ] figures match the FAQ and the chips

### how-to-use

**Job:** How much, when, how long it takes.

**Inputs:** product facts; use-steps

**Evidence:** How-to-use questions customers say the site did not answer.

**Rules:**

- Three lines at most: amount or setting, when, time it takes.
- Names what to use it with when customers ask that.

**Checks:**

- [ ] three lines or fewer
- [ ] matches use-steps

### tabs

**Job:** The details the customer checks before paying.

**Inputs:** product facts (materials, ingredients, specifications); shipping facts; brand guarantee

**Evidence:** What customers would change about the buying experience.

**Rules:**

- The same tabs in the same order on every product: what it is made of (when relevant), shipping, the guarantee.
- Shipping states real ship and delivery times.

**Checks:**

- [ ] same order on every product
- [ ] no tab about another product

## below

### problems-people

**Job:** The customer picks their problem or goal and sees real customers who had it, how long it took, and their photo.

**Inputs:** reviews with photos; results-timeline output

**Evidence:** Reviews with photos and a stated time.

**Rules:**

- One tab per top problem or goal from who-for.
- Each customer: first name, how long it took, their words, their own review photo.

**Artwork:** three real customer photos per tab

**Checks:**

- [ ] every photo comes from its review
- [ ] every customer shows a time

### results-timeline

**Job:** Show when it works, in stages, from the customers' own reviews.

**Inputs:** reviews; scripts/review_timeline.py output

**Evidence:** Every review that states when a change happened.

**Rules:**

- Stages: day 1, week 1, weeks 2-3, weeks 4-6, weeks 7-12, 3+ months. Drop empty stages.
- Each stage: how many reviews, what most of them said changed, two of their own lines, one customer photo when there is one.
- Per product when the product has enough reviews; otherwise the brand's.

**Artwork:** one real customer photo per stage

**Checks:**

- [ ] counts match the script output
- [ ] quotes match reviews exactly

### mechanism

**Job:** How it works, against what the customer does now.

**Inputs:** product facts; avatar language rows: current solutions

**Evidence:** 'How does it work' questions; the alternatives customers name.

**Rules:**

- One comparison: this product against what the customer uses now, yes or no per row.
- Only for products that work by a mechanism the customer cannot see.

**Artwork:** one diagram or close-up

**Checks:**

- [ ] every row is a product fact

### inside

**Job:** What it is made of and what each part does for the customer.

**Inputs:** product facts: parts, materials or ingredients

**Evidence:** Questions about what is in it.

**Rules:**

- One section only, never a second one on the same parts.
- Three to six hero parts, each with what it does for the customer; the full list behind a link or tab.

**Artwork:** one image per hero part; the product's 3D model when the brand has one

**Checks:**

- [ ] appears once on the page
- [ ] every claim is in the product facts

### videos

**Job:** Let the customer watch it work and hear other customers.

**Inputs:** creator and customer footage; brand demo video

**Evidence:** Other customers' results as a reason to buy.

**Rules:**

- One video section: demo first, then customer and creator videos.
- Each tile: a poster frame, the person's name, what changed.

**Artwork:** a poster frame for every tile

**Checks:**

- [ ] no tile without a poster
- [ ] one video section on the page

### use-steps

**Job:** How it is used, in steps, with time per step.

**Inputs:** product facts; the products used together

**Evidence:** Ease of use as a reason customers like it.

**Rules:**

- One step per action (or per product when products are used together), each with its time.
- Real use photos.

**Artwork:** one real use photo per step

**Checks:**

- [ ] steps match how-to-use

### set-contents

**Job:** For a bundle: what each product in it does, with a link to it.

**Inputs:** product facts of each product in the bundle

**Evidence:** -

**Rules:**

- One card per product: name, role, three to five hero parts, a button to its page.

**Artwork:** one product image per card

**Checks:**

- [ ] every card links to its product page
- [ ] names equal store titles

### pairing

**Job:** Add the one product that completes this one, in one tap.

**Inputs:** store variants; brand offers

**Evidence:** Which products customers buy together.

**Rules:**

- Heading and button say it is added to this product.
- The offer-box price look.
- The button adds this product (chosen option) and the pairing together.

**Artwork:** one product image inside its frame

**Checks:**

- [ ] one tap adds both items
- [ ] same price look as the offer box

### guarantee

**Job:** Remove the risk.

**Inputs:** brand guarantee

**Evidence:** -

**Rules:**

- The brand's one guarantee wording everywhere.
- Lead with the length and what the customer gets.
- No other guarantee wording on the page.

**Checks:**

- [ ] one guarantee wording on the whole page

### faq

**Job:** Answer what is left.

**Inputs:** avatar language rows: questions; product facts

**Evidence:** Questions customers say the site did not answer, ranked.

**Rules:**

- One heading on every product.
- The same first questions in the same order on every product, taken from the ranked questions (typically: will it work for me, how long, how to use, what to use it with, is it right for my type or size, how long it lasts), then product-specific ones.
- No answer contradicts the page.

**Checks:**

- [ ] same first questions on every product
- [ ] no contradiction with chips, description or tabs

### reviews

**Job:** Every review, last.

**Inputs:** review app

**Evidence:** -

**Rules:**

- The review app's block, showing the store total.

**Checks:**

- [ ] total equals proof-line

## page

### page-look

**Job:** One look on every product page.

**Inputs:** brand web tokens

**Evidence:** Measured against the best competitor pages with scripts/measure_page.js.

**Rules:**

- One background, at most one contrasting band.
- About twelve text styles; one title size; one button; one accent colour; all from the brand's tokens.
- One section spacing (top/bottom and sides), desktop and phone, from the brand's tokens.
- The whole offer box sits in the first screen on desktop.
- One list-marker style for every list.

**Checks:**

- [ ] text styles counted by scripts/measure_page.js at or under the target
- [ ] no sideways scroll at 390 wide
- [ ] offer box bottom above the fold at 1200 x 800
- [ ] every colour, size and spacing comes from the brand tokens

## Kinds of product

- **single**: One product, used up or used once, that works without a hidden mechanism.
- **single-mechanism**: One product that works by a mechanism the customer cannot see (a tool, a device, a delivery system, an active process).
- **bundle-mechanism**: Several products sold together, one of which works by a hidden mechanism.
- **bundle**: Several products sold together, none with a hidden mechanism; a pairing completes it.

## Recipes: block order per kind

**single**: gallery → proof-line → title → who-for → hero-quote → outcome-chips → offer-box → expectation-line → buy-button → arrival-timeline → objections → description → how-to-use → tabs → problems-people → results-timeline → inside → videos → use-steps → guarantee → faq → reviews

**single-mechanism**: gallery → proof-line → title → who-for → hero-quote → outcome-chips → offer-box → expectation-line → buy-button → arrival-timeline → objections → description → how-to-use → tabs → problems-people → results-timeline → mechanism → inside → videos → use-steps → guarantee → faq → reviews

**bundle-mechanism**: gallery → proof-line → title → who-for → hero-quote → outcome-chips → offer-box → expectation-line → buy-button → arrival-timeline → objections → description → how-to-use → tabs → problems-people → results-timeline → mechanism → inside → set-contents → videos → use-steps → guarantee → faq → reviews

**bundle**: gallery → proof-line → title → who-for → hero-quote → outcome-chips → offer-box → expectation-line → buy-button → arrival-timeline → objections → description → how-to-use → tabs → problems-people → results-timeline → set-contents → pairing → videos → use-steps → guarantee → faq → reviews
