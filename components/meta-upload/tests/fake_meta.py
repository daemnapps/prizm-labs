"""A stand-in for meta.Meta: same calls, nothing leaves the Mac. Used by the
tests and by `approve.py --fake-meta` trials. Every post is kept in `.posts`."""
import itertools
import os
from pathlib import Path

os.environ.setdefault("META_PACE", "off")   # a fake Meta never needs a person's pauses (pace.py)

_ids = itertools.count(9000000001)
WORLD = {}          # account -> {"campaigns": [...], "adsets": [...], "ads": [...]} shared by every FakeMeta


class FakeMeta:
    def __init__(self, brand, fail_on=None):
        from brand import Brand
        self.brand = brand if isinstance(brand, Brand) else Brand(brand)
        self.ACCOUNT = self.brand.account_id
        self.posts = []
        self.gets = []                  # every read: (path, params) — the tests count Meta calls
        self.lists = []                 # every paged list read: path
        self.fail_on = fail_on          # an edge name ("ads", "campaigns") whose post raises Meta's way
        self.w = WORLD.setdefault(self.ACCOUNT, {"campaigns": [], "adsets": [], "ads": []})

    def get(self, path, **params):
        self.gets.append((path, params))
        if path == "" and "ids" in params:          # one status read for many videos
            return {v: {"id": v, "status": {"video_status": "ready"}} for v in params["ids"].split(",")}
        if path.endswith("/ads_volume"):
            return {"data": [{"actor_id": self.brand.page_id, "ads_running_or_in_review_count": 3}]}
        return {"data": []}

    def paged(self, path, **params):
        self.lists.append(path)
        parent, edge = path.rsplit("/", 1)
        return [x for x in self.w.get(edge, []) if x["parent"] == parent]

    def post(self, path, **params):
        if "/" not in path:             # an update on one object (e.g. switching an ad set on)
            self.posts.append(("update", {"id": path, **params}))
            return {"success": True}
        parent, edge = path.rsplit("/", 1)
        self.posts.append((edge, params))
        if self.fail_on == edge:
            raise SystemExit('Meta 400: {"error":{"message":"Invalid parameter (fake)","code":100}}')
        new = {"id": str(next(_ids)), "name": params.get("name")}
        if edge == "adsets":
            parent = params["campaign_id"]
        if edge == "ads":
            parent = params["adset_id"]
        self.w.setdefault(edge, []).append({**new, "parent": parent})
        return {"id": new["id"]}

    def upload_image(self, path, name=None):
        self.posts.append(("adimages", {"name": name}))
        return "hash-" + Path(str(path)).name

    def upload_video(self, path, name=None):
        self.posts.append(("advideos", {"name": name}))
        return "vid-" + str(next(_ids))

    def send_video(self, path, name=None):
        self.posts.append(("advideos", {"name": name}))
        return "vid-" + str(next(_ids))

    def wait_videos(self, ids, names=None, wait=900):
        self.get("", ids=",".join(ids), fields="status")

    def thumbnail_hash(self, vid):
        return "thumb-" + vid
