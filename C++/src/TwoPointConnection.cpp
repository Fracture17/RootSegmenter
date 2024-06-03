#include <vector>
#include <algorithm>
#include <thread>
#include <cmath>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define PI 3.14159265358979323846


static constexpr std::array<int, 8> INDEX_2_R = {{0, -1, -1, -1, 0, 1, 1, 1}};
static constexpr std::array<int, 8> INDEX_2_C = {{1, 1, 0, -1, -1, -1, 0, 1}};
static u8* BRIGHTNESSES;
static u32 WIDTH;

class Crawler {
public:
    int r, c;
    double angle;
    bool canMoveRight, canMoveLeft;
    u32 totalBrightness;
    std::vector<int> historyR;
    std::vector<int> historyC;

    Crawler(u32 r, u32 c, double angle) :
        r(r), c(c), angle(angle), canMoveRight(true), canMoveLeft(true), totalBrightness(0) {}

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

        r += dR;
        c += dC;
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
    for(u32 r = 0; r < height; r++) {
        for(u32 c = 0; c < width; c++) {
            u32 p = r * width + c;
            if(blocked[p]) {
                printf("Blocked: R: %d, C: %d\n", r, c); fflush(stdout);
            }
        }
    }

    int startR = startPos / width;
    int startC = startPos % width;
    int endR = endPos / width;
    int endC = endPos % width;
    printf("R: %d, C: %d\n", startR, startC); fflush(stdout);

    for(u32 i = 0; i < 8; i++) {
        slowCrawlers.emplace_back(startR, startC, PI * (i * .25));
        fastCrawlers.emplace_back(startR, startC, PI * (i * .25));
    }

    std::vector<u32> earlyHistory(5);

    u32 minDistance = std::max(std::abs(startR - endR), std::abs(startC - endC));
    u32 allowedDistance = minDistance * 1.5;
    printf("Distance: %d, %d\n", minDistance, allowedDistance); fflush(stdout);
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

        u32 oldLength = slowCrawlers.size();
        for(u32 j = 0; j < oldLength; j++) {
            auto& c = slowCrawlers[j];

            if(c.canMoveRight) {
                slowCrawlers.push_back(c);
                slowCrawlers.back().moveRight();
            }

            if(c.canMoveLeft) {
                slowCrawlers.push_back(c);
                slowCrawlers.back().moveLeft();
            }

            c.moveForward();
        }

        printf("Hey\n"); fflush(stdout);

        oldLength = fastCrawlers.size();
        for(u32 j = 0; j < oldLength; j++) {
            auto& c = fastCrawlers[j];

            fastCrawlers.push_back(c);
            fastCrawlers.back().moveRight();

            fastCrawlers.push_back(c);
            fastCrawlers.back().moveLeft();

            c.moveForward();
        }

        printf("Hey2\n"); fflush(stdout);

        for(u32 j = 0; j < slowCrawlers.size(); j++) {
            auto& c = slowCrawlers[j];
            if(c.r == endR && c.c == endC) {
                printf("Slow %d\n", i); fflush(stdout);
                return j;
            }
        }

        for(u32 j = 0; j < fastCrawlers.size(); j++) {
            auto& c = fastCrawlers[j];
            if(c.r == endR && c.c == endC) {
                printf("Fast %d\n", i); fflush(stdout);
                return j;
            }
        }

        printf("Crawl: %lld, %lld\n", slowCrawlers.size(), slowCrawlers.capacity()); fflush(stdout);
        printf("Crawl: %lld, %lld\n", fastCrawlers.size(), fastCrawlers.capacity()); fflush(stdout);

        auto blockedCheckFunc = [width, blocked](const Crawler& c) {
            u32 p = c.r * width + c.c;
            return blocked[p];
        };

        auto newEnd = std::remove_if(slowCrawlers.begin(), slowCrawlers.end(), blockedCheckFunc);
        slowCrawlers.erase(newEnd, slowCrawlers.end());

        newEnd = std::remove_if(fastCrawlers.begin(), fastCrawlers.end(), blockedCheckFunc);
        fastCrawlers.erase(newEnd, fastCrawlers.end());

        printf("Crawl: %lld, %lld\n", slowCrawlers.size(), slowCrawlers.capacity()); fflush(stdout);
        printf("Crawl: %lld, %lld\n", fastCrawlers.size(), fastCrawlers.capacity()); fflush(stdout);

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

            printf("Crawl: %lld, %lld\n", slowCrawlers.size(), slowCrawlers.capacity()); fflush(stdout);
            printf("Crawl: %lld, %lld\n", fastCrawlers.size(), fastCrawlers.capacity()); fflush(stdout);
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
        printf("Hey5\n"); fflush(stdout);

        std::sort(fastCrawlers.begin(), fastCrawlers.end(), brightnessCompareFunc);
        printf("Hey5\n"); fflush(stdout);
        limit = std::min((int) (fastCrawlers.size() / 2), 500);
        printf("Hey5\n"); fflush(stdout);
        fastCrawlers.erase(fastCrawlers.begin() + limit, fastCrawlers.end());
        printf("Hey5\n"); fflush(stdout);

        printf("Crawl: %lld, %lld\n", slowCrawlers.size(), slowCrawlers.capacity()); fflush(stdout);
        printf("Crawl: %lld, %lld\n", fastCrawlers.size(), fastCrawlers.capacity()); fflush(stdout);
    }

    for(auto p: earlyHistory) {
        blocked[p] = true;
    }

    return -1;
}


extern "C" void twoPointConnection(u32 startPos, u32 endPos, u8* brightnesses, u32 height, u32 width, u8* results, u8* blocked) {
    BRIGHTNESSES = brightnesses;
    WIDTH = width;

    const u32 MAX_CRAWLERS = 5000;
    std::vector<Crawler> slowCrawlers;
    slowCrawlers.reserve(MAX_CRAWLERS * 3);
    std::vector<Crawler> fastCrawlers;
    fastCrawlers.reserve(MAX_CRAWLERS * 3);

    int result = search(startPos, endPos, height, width, slowCrawlers, fastCrawlers, blocked);
    for(int i = 0; i < 10 && result == -1; i++) {
        printf("Again\n"); fflush(stdout);
        slowCrawlers.clear();
        fastCrawlers.clear();
        result = search(startPos, endPos, height, width, slowCrawlers, fastCrawlers, blocked);
    }

    if(result != -1) {
        results[startPos] = true;

        int endR = endPos / width;
        int endC = endPos % width;
        auto& bestCrawler = (slowCrawlers[result].r == endR && slowCrawlers[result].c == endC) ? slowCrawlers[result] : fastCrawlers[result];

        for(u32 i = 0; i < bestCrawler.historyR.size(); i++) {
            u32 p = bestCrawler.historyR[i] * width + bestCrawler.historyC[i];
            results[p] = true;
        }
    }
}
