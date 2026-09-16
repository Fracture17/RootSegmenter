#include <vector>
#include <algorithm>
#include <thread>
#include <cmath>
#include <array>
#include <cstdio>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define PI 3.14159265358979323846


static constexpr std::array<int, 8> INDEX_2_R = {{0, -1, -1, -1, 0, 1, 1, 1}};
static constexpr std::array<int, 8> INDEX_2_C = {{1, 1, 0, -1, -1, -1, 0, 1}};
static u8* BRIGHTNESSES;
static u32 WIDTH;
static u32 HEIGHT;

class Crawler {
public:
    int r, c;
    double angle;
    bool canMoveRight, canMoveLeft;
    bool dead;
    u32 totalBrightness;
    std::vector<int> historyR;
    std::vector<int> historyC;

    Crawler(u32 r, u32 c, double angle) :
        r(r), c(c), angle(angle), canMoveRight(true), canMoveLeft(true), dead(false), totalBrightness(0) {}

    void moveForward() {
        move(0);

        canMoveRight = true;
        canMoveLeft = true;
    }

    void moveRight() {
        move(-1);

        canMoveRight = false;
        canMoveLeft = true;
    }

    void moveLeft() {
        move(1);

        canMoveRight = true;
        canMoveLeft = false;
    }

private:
    void move(int angleIndexOffset) {
        updateAngle();

        int angleIndex = getAngleIndex();
        angleIndex = (angleIndex + angleIndexOffset + 8) % 8;

        int dR = INDEX_2_R[angleIndex];
        int dC = INDEX_2_C[angleIndex];

        int newR = r + dR;
        int newC = c + dC;

        //A crawler that steps off the image has no brightness to read.  Mark it dead
        //and let the caller drop it.  Without this the index below goes outside the
        //brightness buffer, and a negative position wraps to an enormous u32.
        if(newR < 0 || newR >= (int) HEIGHT || newC < 0 || newC >= (int) WIDTH) {
            dead = true;
            return;
        }

        r = newR;
        c = newC;
        historyR.push_back(r);
        historyC.push_back(c);

        u32 i = r * WIDTH + c;
        totalBrightness += BRIGHTNESSES[i];
    }

    void updateAngle() {
        if(historyR.size() > 2) {
            int i = std::max((int) (historyR.size() - 6), 0);
            int startR = historyR[i];
            int startC = historyC[i];

            int dy = r - startR;
            int dx = startC - c;
            angle = atan2(dy, dx) + PI;
        }
    }

    int getAngleIndex() {
        auto index = (int) ((fmod(angle + PI / 8 - .01, PI * 2) / PI) * 4);
        return index;
    }
};


int search(u32 startPos, u32 endPos, u32 height, u32 width, std::vector<Crawler>& slowCrawlers, std::vector<Crawler>& fastCrawlers, u8* blocked) {
    int startR = startPos / width;
    int startC = startPos % width;
    int endR = endPos / width;
    int endC = endPos % width;

    for(u32 i = 0; i < 8; i++) {
        slowCrawlers.emplace_back(startR, startC, PI * (i * .25));
        fastCrawlers.emplace_back(startR, startC, PI * (i * .25));
    }

    std::vector<u32> earlyHistory(5);
    std::vector<Crawler> children;

    u32 minDistance = std::max(std::abs(startR - endR), std::abs(startC - endC));
    u32 allowedDistance = minDistance * 1.5;
    for(u32 i = 0; i < allowedDistance; i++) {
        if(slowCrawlers.size() > 5000) {
            slowCrawlers.clear();
        }
        if(fastCrawlers.size() > 5000) {
            fastCrawlers.clear();
        }
        if(slowCrawlers.size() == 0 && fastCrawlers.size() == 0) {
            break;
        }

        //Children are collected separately and appended afterwards.  Pushing onto the
        //same vector while holding a reference into it is undefined behaviour as soon
        //as the vector reallocates.
        u32 oldLength = slowCrawlers.size();
        children.clear();
        for(u32 j = 0; j < oldLength; j++) {
            auto& c = slowCrawlers[j];

            if(c.canMoveRight) {
                children.push_back(c);
                children.back().moveRight();
            }

            if(c.canMoveLeft) {
                children.push_back(c);
                children.back().moveLeft();
            }

            c.moveForward();
        }
        slowCrawlers.insert(slowCrawlers.end(), children.begin(), children.end());

        oldLength = fastCrawlers.size();
        children.clear();
        for(u32 j = 0; j < oldLength; j++) {
            auto& c = fastCrawlers[j];

            children.push_back(c);
            children.back().moveRight();

            children.push_back(c);
            children.back().moveLeft();

            c.moveForward();
        }
        fastCrawlers.insert(fastCrawlers.end(), children.begin(), children.end());

        for(u32 j = 0; j < slowCrawlers.size(); j++) {
            auto& c = slowCrawlers[j];
            if(!c.dead && c.r == endR && c.c == endC) {
                return j;
            }
        }

        for(u32 j = 0; j < fastCrawlers.size(); j++) {
            auto& c = fastCrawlers[j];
            if(!c.dead && c.r == endR && c.c == endC) {
                return j;
            }
        }

        //Drops crawlers that left the image as well as blocked ones.  The bounds check
        //has to come first, since a dead crawler's position is not a valid index.
        auto shouldRemoveFunc = [width, height, blocked](const Crawler& c) {
            if(c.dead) {
                return true;
            }
            if(c.r < 0 || c.r >= (int) height || c.c < 0 || c.c >= (int) width) {
                return true;
            }
            u32 p = c.r * width + c.c;
            return (bool) blocked[p];
        };

        auto newEnd = std::remove_if(slowCrawlers.begin(), slowCrawlers.end(), shouldRemoveFunc);
        slowCrawlers.erase(newEnd, slowCrawlers.end());

        newEnd = std::remove_if(fastCrawlers.begin(), fastCrawlers.end(), shouldRemoveFunc);
        fastCrawlers.erase(newEnd, fastCrawlers.end());

        /*if(restrictDistance) {
            u32 remainingDistance = allowedDistance - i;
            auto distanceCheckFunc = [remainingDistance, endR, endC](const Crawler& c) {
                u32 crawlerDistance = std::max(std::abs(c.r - endR), std::abs(c.c - endC));
                return crawlerDistance > remainingDistance;
            };

            auto newEnd = std::remove_if(slowCrawlers.begin(), slowCrawlers.end(), distanceCheckFunc);
            slowCrawlers.erase(newEnd, slowCrawlers.end());

            newEnd = std::remove_if(fastCrawlers.begin(), fastCrawlers.end(), distanceCheckFunc);
            fastCrawlers.erase(newEnd, fastCrawlers.end());

            printf("Crawl: %zu, %zu\n", slowCrawlers.size(), slowCrawlers.capacity()); fflush(stdout);
            printf("Crawl: %zu, %zu\n", fastCrawlers.size(), fastCrawlers.capacity()); fflush(stdout);
        }*/

        if(slowCrawlers.size() > 0 && slowCrawlers[0].historyR.size() > 5) {
            for(int j = 0; j < 5; j++) {
                u32 p = slowCrawlers[0].historyR[j] * width + slowCrawlers[0].historyC[j];
                earlyHistory[j] = p;
            }
        }

        auto brightnessCompareFunc = [](const Crawler& a, const Crawler& b) {
            return a.totalBrightness > b.totalBrightness;
        };

        std::sort(slowCrawlers.begin(), slowCrawlers.end(), brightnessCompareFunc);
        u32 limit = std::min((int) (slowCrawlers.size() / 2), 500);
        slowCrawlers.erase(slowCrawlers.begin() + limit, slowCrawlers.end());

        std::sort(fastCrawlers.begin(), fastCrawlers.end(), brightnessCompareFunc);
        limit = std::min((int) (fastCrawlers.size() / 2), 500);
        fastCrawlers.erase(fastCrawlers.begin() + limit, fastCrawlers.end());
    }

    for(auto p: earlyHistory) {
        blocked[p] = true;
    }

    return -1;
}


extern "C" void twoPointConnection(u32 startPos, u32 endPos, u8* brightnesses, u32 height, u32 width, u8* results, u8* blocked) {
    BRIGHTNESSES = brightnesses;
    WIDTH = width;
    HEIGHT = height;

    const u32 MAX_CRAWLERS = 5000;
    std::vector<Crawler> slowCrawlers;
    slowCrawlers.reserve(MAX_CRAWLERS * 3);
    std::vector<Crawler> fastCrawlers;
    fastCrawlers.reserve(MAX_CRAWLERS * 3);

    int result = search(startPos, endPos, height, width, slowCrawlers, fastCrawlers, blocked);
    for(int i = 0; i < 10 && result == -1; i++) {
        slowCrawlers.clear();
        fastCrawlers.clear();
        result = search(startPos, endPos, height, width, slowCrawlers, fastCrawlers, blocked);
    }

    if(result != -1) {
        int endR = endPos / width;
        int endC = endPos % width;

        //The index came from whichever vector found the endpoint first, so it is only
        //valid for that one.  Checking the size matters because the two vectors are
        //pruned independently and often have different lengths.
        const Crawler* bestCrawler = nullptr;
        if(result < (int) slowCrawlers.size() && slowCrawlers[result].r == endR && slowCrawlers[result].c == endC) {
            bestCrawler = &slowCrawlers[result];
        } else if(result < (int) fastCrawlers.size() && fastCrawlers[result].r == endR && fastCrawlers[result].c == endC) {
            bestCrawler = &fastCrawlers[result];
        }

        if(bestCrawler != nullptr) {
            results[startPos] = true;

            for(u32 i = 0; i < bestCrawler->historyR.size(); i++) {
                u32 p = bestCrawler->historyR[i] * width + bestCrawler->historyC[i];
                results[p] = true;
            }
        }
    }
}
