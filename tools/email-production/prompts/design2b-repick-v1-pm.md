# Design step 2b · choose the pictures again, change nothing else

Every brand, product and name below comes from THIS email's own inputs. Never bring in anything from elsewhere.

The email below is laid out and its words are approved. A person already ruled on its sections, its order and
every word in it. Your one job is its real pictures: each numbered slot holds a photo or a customer picture
the brand owns, and the layout chose it before anyone could see what it shows. Now every picture we own is
listed with what is IN it. For each slot, decide whether the picture there fits the words it sits with.

{learnings}

<the_job_card>
{concept}
</the_job_card>

<what_this_email_sells>
{sells}
</what_this_email_sells>

<the_slots>
{slots}
</the_slots>

<brand_photos_we_own>
{photos}
</brand_photos_we_own>

<real_proof_you_may_use>
{proof}
</real_proof_you_may_use>

<already_used_in_other_emails_this_month>
{used}
</already_used_in_other_emails_this_month>

## How to choose

1. KEEP the picture in a slot when what it shows fits the words around it. Keeping is the default; change a
   picture only for a reason you can name.
2. CHANGE it when it shows something the words do not say, a person who is not the reader, a product this
   email does not sell, or anything the JOB CARD's `cut` rules out. Choose from BRAND PHOTOS or REAL PROOF only, by what each line says is in the picture —
   never by its file name. Never a picture listed as already used in another email, never one picture twice in
   this email. A customer's own words sit only with that customer's own picture.
3. When nothing we own shows what the words say, say what the slot needs as a picture to make: `todo` (what it
   shows, plainly) and `brief` (the shot, the real reference it starts from, which real product is in it). A real
   picture beats a made one only when it shows what the words say: never pick the nearest owned picture for a
   slot it does not fit — a wrong real picture is what this step exists to remove. A picture to make carries
   no words: no labels, captions or claims set into it. The email's words are ruled; a picture never adds to them.

## Answer

Only JSON, one entry per slot, in slot order:

{"slots": [{"n": 1, "keep": true, "why": "..."},
           {"n": 2, "photo": "<ref from BRAND PHOTOS>", "why": "..."},
           {"n": 3, "proof": "<id from REAL PROOF>", "why": "..."},
           {"n": 4, "todo": "...", "brief": "...", "why": "..."}]}
