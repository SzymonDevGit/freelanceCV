package uk.co.cheltenhamdata.rately;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.UUID;

/** One tier list: its tiers (best first), the pictures in each, and the queue still to rate. */
final class TierList {

    static final class Tier {
        String id;
        String label;
        int color;
        final ArrayList<Item> items = new ArrayList<>();

        String shownLabel() {
            String l = label == null ? "" : label.trim();
            return l.isEmpty() ? "?" : l;
        }
    }

    static final class Item {
        String id;
        /** File name inside Store.imagesDir(). */
        String image;
    }

    private static final String[] DEFAULT_LABELS = {"S", "A", "B", "C", "D", "F"};
    private static final String NEXT_LABELS = "SABCDEFGHIJKLMNOPQRTUVWXYZ";

    String id;
    String name;
    long created;
    long updated;
    final ArrayList<Tier> tiers = new ArrayList<>();
    /** Pictures waiting to be rated, in the order the quick-rate screen shows them. */
    final ArrayList<Item> queue = new ArrayList<>();

    static TierList create(String name) {
        TierList l = new TierList();
        l.id = newId();
        l.name = name;
        l.created = l.updated = System.currentTimeMillis();
        for (int i = 0; i < DEFAULT_LABELS.length; i++) {
            l.tiers.add(newTier(DEFAULT_LABELS[i], Toon.TIER_COLORS[i]));
        }
        return l;
    }

    static Tier newTier(String label, int color) {
        Tier t = new Tier();
        t.id = newId();
        t.label = label;
        t.color = color;
        return t;
    }

    static Item newItem(String image) {
        Item it = new Item();
        it.id = newId();
        it.image = image;
        return it;
    }

    private static String newId() {
        return UUID.randomUUID().toString();
    }

    int size() {
        int n = queue.size();
        for (Tier t : tiers) n += t.items.size();
        return n;
    }

    /** Every picture in board order: tiers best first, then the queue. */
    ArrayList<Item> allItems() {
        ArrayList<Item> all = new ArrayList<>();
        for (Tier t : tiers) all.addAll(t.items);
        all.addAll(queue);
        return all;
    }

    Item findItem(String itemId) {
        for (Item it : allItems()) {
            if (it.id.equals(itemId)) return it;
        }
        return null;
    }

    /** The tier holding the item, or null when it is in the queue (or gone). */
    Tier tierOf(Item it) {
        for (Tier t : tiers) {
            if (t.items.contains(it)) return t;
        }
        return null;
    }

    private ArrayList<Item> holder(Item it) {
        if (queue.contains(it)) return queue;
        Tier t = tierOf(it);
        return t == null ? null : t.items;
    }

    /** Moves an item into a tier, or the queue when target is null, at index (clamped). */
    void move(Item it, Tier target, int index) {
        ArrayList<Item> to = target == null ? queue : target.items;
        ArrayList<Item> from = holder(it);
        if (from != null) {
            int old = from.indexOf(it);
            from.remove(old);
            if (from == to && old < index) index--;
        }
        to.add(Math.max(0, Math.min(index, to.size())), it);
    }

    void remove(Item it) {
        ArrayList<Item> from = holder(it);
        if (from != null) from.remove(it);
    }

    /** Deletes a tier; its pictures go to the end of the queue. */
    void removeTier(Tier t) {
        queue.addAll(t.items);
        t.items.clear();
        tiers.remove(t);
    }

    /** Sends every rated picture back to the queue, best tier first. */
    void unrateAll() {
        ArrayList<Item> rated = new ArrayList<>();
        for (Tier t : tiers) {
            rated.addAll(t.items);
            t.items.clear();
        }
        queue.addAll(0, rated);
    }

    String nextLabel() {
        for (int i = 0; i < NEXT_LABELS.length(); i++) {
            String l = String.valueOf(NEXT_LABELS.charAt(i));
            boolean used = false;
            for (Tier t : tiers) {
                if (l.equalsIgnoreCase(t.shownLabel())) used = true;
            }
            if (!used) return l;
        }
        return "?";
    }

    int nextColor() {
        for (int c : Toon.TIER_COLORS) {
            boolean used = false;
            for (Tier t : tiers) {
                if (t.color == c) used = true;
            }
            if (!used) return c;
        }
        return Toon.TIER_COLORS[tiers.size() % Toon.TIER_COLORS.length];
    }

    // ---- JSON ------------------------------------------------------------------------------------

    JSONObject toJson() throws JSONException {
        JSONObject o = new JSONObject();
        o.put("v", 1);
        o.put("id", id);
        o.put("name", name);
        o.put("created", created);
        o.put("updated", updated);
        JSONArray ts = new JSONArray();
        for (Tier t : tiers) {
            JSONObject to = new JSONObject();
            to.put("id", t.id);
            to.put("label", t.label);
            to.put("color", t.color);
            to.put("items", items(t.items));
            ts.put(to);
        }
        o.put("tiers", ts);
        o.put("queue", items(queue));
        return o;
    }

    private static JSONArray items(ArrayList<Item> list) throws JSONException {
        JSONArray a = new JSONArray();
        for (Item it : list) {
            JSONObject io = new JSONObject();
            io.put("id", it.id);
            io.put("img", it.image);
            a.put(io);
        }
        return a;
    }

    static TierList fromJson(JSONObject o) throws JSONException {
        TierList l = new TierList();
        l.id = o.getString("id");
        l.name = o.optString("name", "Tier list");
        l.created = o.optLong("created");
        l.updated = o.optLong("updated");
        JSONArray ts = o.optJSONArray("tiers");
        for (int i = 0; ts != null && i < ts.length(); i++) {
            JSONObject to = ts.getJSONObject(i);
            Tier t = new Tier();
            t.id = to.getString("id");
            t.label = to.optString("label", "?");
            t.color = to.optInt("color", Toon.TIER_COLORS[i % Toon.TIER_COLORS.length]);
            readItems(to.optJSONArray("items"), t.items);
            l.tiers.add(t);
        }
        readItems(o.optJSONArray("queue"), l.queue);
        return l;
    }

    private static void readItems(JSONArray a, ArrayList<Item> into) throws JSONException {
        for (int i = 0; a != null && i < a.length(); i++) {
            JSONObject io = a.getJSONObject(i);
            Item it = new Item();
            it.id = io.getString("id");
            it.image = io.getString("img");
            into.add(it);
        }
    }
}
