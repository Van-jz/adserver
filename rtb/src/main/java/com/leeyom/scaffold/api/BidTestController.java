package com.leeyom.scaffold.api;


import cn.hutool.core.util.RandomUtil;
import cn.hutool.json.JSONUtil;
import com.leeyom.scaffold.common.exception.BizException;
import com.leeyom.scaffold.dto.req.BidRequest;
import com.leeyom.scaffold.dto.resp.Bid;
import com.leeyom.scaffold.dto.resp.BidResp;
import com.leeyom.scaffold.dto.resp.Seatbid;
import com.leeyom.scaffold.enums.AdvChoiceStrategyEnum;
import com.leeyom.scaffold.enums.GenderEnum;
import com.leeyom.scaffold.enums.OsEnum;
import com.leeyom.scaffold.factory.*;
import com.leeyom.scaffold.service.BidReqLogService;
import com.leeyom.scaffold.utils.DateUtils;
import com.leeyom.scaffold.utils.SnowFlakeIdUtil;
import lombok.extern.slf4j.Slf4j;
import org.apache.ibatis.annotations.Param;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StringUtils;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.math.BigDecimal;
import java.util.*;

/**
 * 根据ssp请求向广告平台竞价
 *
 * @author luoxun
 * @since 2025-05-20 09:17:37
 */
@RestController
@RequestMapping("test/rtb")
@Slf4j
public class BidTestController {

    @Resource
    private BidReqLogService service;

    @Resource
    private AdvertChoiceFactory advertChoiceFactory;

    @Value("${strategy:}")
    private String strategy;

    @Resource
    private AdvertChoiceBidOnePer1000 advertChoiceBidOnePer1000;

    private static final String CUR = "USD";

    private static final List<String> SEAT_LIST = Arrays.asList("7735", "7736", "7737", "7738", "7739");

    private static final List<String> BUNDLE_ANDROID_LIST = Arrays.asList("com.supercell.hayday", "com.jztech", "com.globalgoogleplay", "com.7373", "com.5177");

    private static final List<String> BUNDLE_IOS_LIST = Arrays.asList("1000337", "1209386", "7755378", "99001457", "83864521");


    private static final String NURL = "https://dsp.globalgoogleplay.com/dev/rtb/notice/won?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}"; //竞价win通知url

    private static final String BURL = "https://dsp.globalgoogleplay.com/dev/rtb/notice/bid?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}"; //竞价通知url

    private static final String LURL = "https://dsp.globalgoogleplay.com/dev/rtb/notice/lose?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}"; //竞价失败通知url

    private static final List<String> ADOMAIN = Arrays.asList("advertiserdomain.com");

    private static final List<Advert> waitChooseAdvertList = new ArrayList<>();

    private static final Map<String, Advert> waitChooseAdvertMap = new HashMap<>();

    private static final String BID_PRICE = "1";

    static {
        Advert advert1 = new Advert();
        advert1.setId("1");
        advert1.setName("ap777");
//        advert1.setLinkUrl("https://www.ap777.ws/#/?fb=1235604878311848&code=0rvr");
        advert1.setAdm("<VAST version=\"2.0\">" +
                "<Ad>" +
                "<InLine>" +
                "<AdTitle>BET777</AdTitle>" +
                "<Impression>" +
                "<![CDATA[https://static.globalgoogleplay.com/material/1/BET777.jpg]]>" +
                "</Impression>" +
                "<Creatives>" +
                "<Creative id=\"57767c29a63510e75f000073\">" +
                "<Linear>" +
                "<Duration>00:00:18</Duration>" +
                "<TrackingEvents>" +
                "<Tracking event=\"start\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/startPlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "<Tracking event=\"complete\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/completePlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "</TrackingEvents>" +
                "<VideoClicks>" +
                "<ClickThrough><![CDATA[https://www.ap777.ws/#/?fb=1235604878311848&code=0rvr?ttdsp_price]]></ClickThrough>" +
                "<ClickTracking><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/click?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></ClickTracking>" +
                "</VideoClicks>" +
                "<MediaFiles>" +
                "<MediaFile delivery=\"progressive\" type=\"video/mp4\" width=\"1280\" height=\"720\"> " +
                "<![CDATA[https://static.globalgoogleplay.com/material/1/BET777.mp4]]>" +
                "</MediaFile>" +
                "</MediaFiles>" +
                "</Linear>" +
                "</Creative>" +
                "</Creatives>" +
                "<Description>Uma nova plataforma online com múltiplas opções de jogo e uma alta taxa de explosivos. Registre-se e receba um grande presente. Bem-vindo para se juntar.</Description>" +
                "</InLine>" +
                "</Ad>" +
                "</VAST>");
        advert1.setBidPrice(new BigDecimal(BID_PRICE));
        StrategyParam strategyParam1 = new StrategyParam();
        strategyParam1.setAgeMin(18);
        strategyParam1.setAgeMax(60);
        // 中国：CHN  美国：USA 日本：JPN 德国：DEU
        strategyParam1.setCountryList(Arrays.asList("USA"));
        strategyParam1.setRegionList(Arrays.asList("ND", "OH"));
        strategyParam1.setGenderList(Arrays.asList(GenderEnum.FEMALE.getValue()));
        advert1.setCid("554d550b418461cc3700014d");
        advert1.setCrid("57767c29a63510e75f000073");
        advert1.setStrategyParam(strategyParam1);
        waitChooseAdvertList.add(advert1);

        Advert advert2 = new Advert();
        advert2.setId("2");
        advert2.setName("sorteios");
//        advert2.setLinkUrl("https://play.google.com/store/apps/details?id=beatmaker.edm.musicgames.PianoGames");
        advert2.setBidPrice(new BigDecimal(BID_PRICE));
        advert2.setAdm("<VAST version=\"2.0\">" +
                "<Ad>" +
                "<InLine>" +
                "<AdTitle>\uD83D\uDD252000 sorteios de prêmios grátis\uD83D\uDD25</AdTitle>" +
                "<Impression>" +
                "<![CDATA[https://static.globalgoogleplay.com/material/2/TokyoGhoulBreaktheChains.jpg]]>" +
                "</Impression>" +
                "<Creatives>" +
                "<Creative id=\"57167c29a63810e75f00807e\">" +
                "<Linear>" +
                "<Duration>00:00:18</Duration>" +
                "<TrackingEvents>" +
                "<Tracking event=\"start\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/startPlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "<Tracking event=\"complete\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/completePlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "</TrackingEvents>" +
                "<VideoClicks>" +
                "<ClickThrough><![CDATA[https://play.google.com/store/apps/details?id=com.funcat.tgbtc]]></ClickThrough>" +
                "<ClickTracking><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/click?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></ClickTracking>" +
                "</VideoClicks>" +
                "<MediaFiles>" +
                "<MediaFile delivery=\"progressive\" type=\"video/mp4\" width=\"1280\" height=\"720\"> " +
                "<![CDATA[https://static.globalgoogleplay.com/material/2/TokyoGhoulBreaktheChainsmain.mp4]]>" +
                "</MediaFile>" +
                "</MediaFiles>" +
                "</Linear>" +
                "</Creative>" +
                "</Creatives>" +
                "<Description>\uD83D\uDCA5O que é 1000-7? \uD83D\uDCA5✅RPG oficial de Tokyo Ghoul\uD83D\uDD25Mais de um milhão de jogadores online\uD83E\uDD73Faça login para obter o passe mensal + 2000 sorteios</Description>" +
                "</InLine>" +
                "</Ad>" +
                "</VAST>");
        StrategyParam strategyParam2 = new StrategyParam();
        strategyParam2.setAgeMin(22);
        strategyParam2.setAgeMax(55);
        // 中国：CHN  美国：USA 日本：JPN 德国：DEU
        strategyParam2.setCountryList(Arrays.asList("CHN"));
        strategyParam2.setRegionList(Arrays.asList("CN-JX", "CN-BJ", "CN-SH"));
        strategyParam2.setGenderList(Arrays.asList(GenderEnum.MALE.getValue()));
        advert2.setCid("154d750b418461dc3701018d");
        advert2.setCrid("57167c29a63810e75f00807e");
        advert2.setStrategyParam(strategyParam2);
        waitChooseAdvertList.add(advert2);

        Advert advert3 = new Advert();
        advert3.setId("3");
        advert3.setName("Comece");
//        advert3.setLinkUrl("https://play.google.com/store/apps/details?id=com.goldenjogos.game&ttclid=E_C_P_CscBEDf9yBzhvONJqe_7f5BKqXbmm1aBnqoaq-6UekGtv_cLlH7gXxorB48Ma6Gnvuc6ZuQ9oxYZCRKr9rN35ZxkjRLa39PbxCvRh0aMIpixLZc74a5k9X_3XjGdbRn6Tcor7XuTd69nTYRGX3k2MpsZXV0lOXb6m1IA5y4n18DhtBqkRunOhxPZBejmPGuznya7od-vEADXjFgZ5PkSyqpoScvjzKqDum53SgnDns_SQliVI6rmCaBT18dR96BxCQbYNq4ldEeFaRIEdjIuMA");
        advert3.setAdm("" +
                "<VAST version=\"2.0\">" +
                "<Ad>" +
                "<InLine>" +
                "<AdTitle>Comece a ganhar agora!\uD83D\uDC49</AdTitle>" +
                "<Impression>" +
                "<![CDATA[https://static.globalgoogleplay.com/material/3/KTSlotsmain.jpg]]>" +
                "</Impression>" +
                "<Creatives>" +
                "<Creative id=\"17167119a63810e75f108071\">" +
                "<Linear>" +
                "<Duration>00:00:18</Duration>" +
                "<TrackingEvents>" +
                "<Tracking event=\"start\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/startPlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "<Tracking event=\"complete\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/completePlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "</TrackingEvents>" +
                "<VideoClicks>" +
                "<ClickThrough><![CDATA[https://apps62.googleplpay.com/?p0=1ecsuwp4&p1={{campaign.name}}&p2={{campaign.id}}&p3={{adset.name}}&p4={{adset.id}}&p5={{ad.name}}&p6={{ad.id}}]]></ClickThrough>" +
                "<ClickTracking><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/click?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></ClickTracking>" +
                "</VideoClicks>" +
                "<MediaFiles>" +
                "<MediaFile delivery=\"progressive\" type=\"video/mp4\" width=\"1280\" height=\"720\"> " +
                "<![CDATA[]]>" +
                "</MediaFile>" +
                "</MediaFiles>" +
                "</Linear>" +
                "</Creative>" +
                "</Creatives>" +
                "<Description>\uD83D\uDCE3Nova plataforma, alta taxa de vitórias\uD83C\uDF1F Jogue agora e experimente a emoção de ganhar! \uD83C\uDF1F</Description>" +
                "</InLine>" +
                "</Ad>" +
                "</VAST>");
        advert3.setBidPrice(new BigDecimal(BID_PRICE));
        StrategyParam strategyParam3 = new StrategyParam();
        strategyParam3.setAgeMin(18);
        strategyParam3.setAgeMax(60);
        // 中国：CHN  美国：USA 日本：JPN 德国：DEU
        strategyParam3.setCountryList(Arrays.asList("USA", "CHN"));
        strategyParam3.setRegionList(Arrays.asList("ND", "OH"));
        strategyParam3.setGenderList(Arrays.asList(""));
        advert3.setStrategyParam(strategyParam3);
        advert3.setCid("954d659b418461dc37610689");
        advert3.setCrid("17167119a63810e75f108071");
        waitChooseAdvertList.add(advert3);

        Advert advert4 = new Advert();
        advert4.setId("4");
        advert4.setName("kamagames");
//        advert4.setLinkUrl("https://play.google.com/store/apps/details?id=com.kamagames.roulettist&hl=en&gl=US&ttclid=E_C_P_CsgBcbN53zsmYUoFdD83AKlS_tI7u4hPoyIY3x7g3AzdphbC2UpHbckJkNDQMXKt3tBXGK1W4yh1Y-6ALswri4KmcJQf65KKL97J-QkjHf44goIiUoLXbXSE38DgHcZb-Ehjh_5mbbbhRoDIO2IxeclVL-bprxTs38zknD-CRLUHb5_bg6A8PUNW5CKxPFoYm-uKEiJ1e1gCzv-8BEwfCta6imc41Lv-Gpkp-AZUdXEW4GJKLeFuW6PAQg2Tt1Z4HM_9dfQx9rgtW3QSBHYyLjA");
        advert4.setBidPrice(new BigDecimal(BID_PRICE));
        advert4.setAdm("<VAST version=\"2.0\">" +
                "<Ad>" +
                "<InLine>" +
                "<AdTitle>OK Slots</AdTitle>" +
                "<Impression>" +
                "<![CDATA[https://static.globalgoogleplay.com/material/4/OKSlots.jpg]]>" +
                "</Impression>" +
                "<Creatives>" +
                "<Creative id=\"37667319a63810375f608371\">" +
                "<Linear>" +
                "<Duration>00:00:18</Duration>" +
                "<TrackingEvents>" +
                "<Tracking event=\"start\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/startPlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "<Tracking event=\"complete\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/completePlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "</TrackingEvents>" +
                "<VideoClicks>" +
                "<ClickThrough><![CDATA[https://play16.okslotsok.com/?p0=1f1spf6m&amp;p1=%7B%7Bcampaign.name%7D%7D&amp;p2=%7B%7Bcampaign.id%7D%7D&amp;p3=%7B%7Badset.name%7D%7D&amp;p4=%7B%7Badset.id%7D%7D&amp;p5=%7B%7Bad.name%7D%7D&amp;p6=%7B%7Bad.id%7D%7D]]></ClickThrough>" +
                "<ClickTracking><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/click?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></ClickTracking>" +
                "</VideoClicks>" +
                "<MediaFiles>" +
                "<MediaFile delivery=\"progressive\" type=\"video/mp4\" width=\"1280\" height=\"720\"> " +
                "<![CDATA[https://static.globalgoogleplay.com/material/4/OKSlotsmain.mp4]]>" +
                "</MediaFile>" +
                "</MediaFiles>" +
                "</Linear>" +
                "</Creative>" +
                "</Creatives>" +
                "<Description>\uD83D\uDD25PG Slots \uD83D\uDD25PG Slots\uD83D\uDD25\uD83C\uDF81Novo jogo lanGadopela primeira vez✨Registre se para obter beneficios✨✅Sem anúncios ✅Sem limites de retir</Description>" +
                "</InLine>" +
                "</Ad>" +
                "</VAST>");
        StrategyParam strategyParam4 = new StrategyParam();
//        strategyParam4.setAgeMin(18);
//        strategyParam4.setAgeMax(60);
        // 中国：CHN  美国：USA 日本：JPN 德国：DEU
//        strategyParam4.setCountryList(Arrays.asList("USA"));
//        strategyParam4.setRegionList(Arrays.asList("ND", "OH"));
//        strategyParam4.setGenderList(Arrays.asList(GenderEnum.FEMALE.getValue()));
        advert4.setStrategyParam(strategyParam4);
        advert4.setCid("254d252b418421dc37210682");
        advert4.setCrid("37667319a63810375f608371");
        waitChooseAdvertList.add(advert4);

        Advert advert5 = new Advert();
        advert5.setId("5");
        advert5.setName("betnacional");
//        advert5.setLinkUrl("https://aposte.betnacional.bet.br/?token=OwJjrM9rZhYv7tlLtFOEmmNd7ZgqdRLk&");
        advert5.setAdm("<VAST version=\"2.0\">" +
                "<Ad>" +
                "<InLine>" +
                "<AdTitle>OK Slots</AdTitle>" +
                "<Impression>" +
                "<![CDATA[https://static.globalgoogleplay.com/material/5/OKSlots.jpg]]>" +
                "</Impression>" +
                "<Creatives>" +
                "<Creative id=\"35677319a638503757608377\">" +
                "<Linear>" +
                "<Duration>00:00:18</Duration>" +
                "<TrackingEvents>" +
                "<Tracking event=\"start\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/startPlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "<Tracking event=\"complete\"><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/completePlay?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></Tracking>" +
                "</TrackingEvents>" +
                "<VideoClicks>" +
                "<ClickThrough><![CDATA[https://play16.okslotsok.com/?p0=1f1spf6m&amp;p1=%7B%7Bcampaign.name%7D%7D&amp;p2=%7B%7Bcampaign.id%7D%7D&amp;p3=%7B%7Badset.name%7D%7D&amp;p4=%7B%7Badset.id%7D%7D&amp;p5=%7B%7Bad.name%7D%7D&amp;p6=%7B%7Bad.id%7D%7D]]></ClickThrough>" +
                "<ClickTracking><![CDATA[https://dsp.globalgoogleplay.com/prod/rtb/track/click?adid=${AUCTION_AD_ID}&price=${AUCTION_PRICE}&bidid=${AUCTION_BID_ID}]]></ClickTracking>" +
                "</VideoClicks>" +
                "<MediaFiles>" +
                "<MediaFile delivery=\"progressive\" type=\"video/mp4\" width=\"1280\" height=\"720\"> " +
                "<![CDATA[https://static.globalgoogleplay.com/material/5/OKSlots.mp4]]>" +
                "</MediaFile>" +
                "</MediaFiles>" +
                "</Linear>" +
                "</Creative>" +
                "</Creatives>" +
                "<Description>\uD83D\uDD25PG Slots \uD83D\uDD25PG Slots\uD83D\uDD25\uD83C\uDF81Novo jogo lanGadopela primeira vez✨Registre se para obter beneficios✨✅Sem anúncios ✅Sem limites de retir</Description>" +
                "</InLine>" +
                "</Ad>" +
                "</VAST>");
        advert5.setBidPrice(new BigDecimal(BID_PRICE));
        StrategyParam strategyParam5 = new StrategyParam();
        strategyParam5.setAgeMin(18);
        strategyParam5.setAgeMax(60);
        // 中国：CHN  美国：USA 日本：JPN 德国：DEU
//        strategyParam5.setCountryList(Arrays.asList("USA"));
//        strategyParam5.setRegionList(Arrays.asList("ND", "OH"));
        strategyParam5.setGenderList(Arrays.asList(GenderEnum.FEMALE.getValue()));
        advert5.setCid("755d252b4187215c37510685");
        advert5.setCrid("35677319a638503757608377");
        advert5.setStrategyParam(strategyParam5);
        waitChooseAdvertList.add(advert5);

        waitChooseAdvertMap.put(advert1.getId(), advert1);
        waitChooseAdvertMap.put(advert2.getId(), advert2);
        waitChooseAdvertMap.put(advert3.getId(), advert3);
        waitChooseAdvertMap.put(advert4.getId(), advert4);
        waitChooseAdvertMap.put(advert5.getId(), advert5);

    }

    @GetMapping("/change/interval/{interval}")
    public ResponseEntity<Boolean> changeInterval(@PathVariable("interval") Integer interval) {
        advertChoiceBidOnePer1000.setINTERVAL(interval);
        return new ResponseEntity<>(true, HttpStatus.OK);
    }


    @RequestMapping("/notice/won")
    public ResponseEntity<Boolean> won(@Param("adid") String adid, @Param("bidid") String bidid, @Param("price") BigDecimal price) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");
        log.info("{} won ,price ={}", adid, price);
        return new ResponseEntity<>(true, headers, HttpStatus.OK);
    }

    @RequestMapping("/notice/lose")
    public ResponseEntity<Boolean> lose(@Param("adid") String adid, @Param("bidid") String bidid, @Param("price") BigDecimal price) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");
        log.info("{} lose ", adid);
        return new ResponseEntity<>(true, headers, HttpStatus.OK);
    }

    @RequestMapping("/notice/bid")
    public ResponseEntity<String> bid(@Param("adid") String adid, @Param("bidid") String bidid, @Param("price") BigDecimal price) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");
        log.info("{} bid ", adid);
        String adm = "";
        Advert advert = waitChooseAdvertMap.get(adid);
        if (advert != null) {
            adm = advert.getAdm();
        }
        return new ResponseEntity<>(adm, headers, HttpStatus.OK);
    }

    @RequestMapping("/track/startPlay")
    public ResponseEntity<Boolean> startPlay(@Param("adid") String adid, @Param("bidid") String bidid, @Param("price") BigDecimal price) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");
        log.info("startPlay {} bid ", adid);
        return new ResponseEntity<>(true, headers, HttpStatus.OK);
    }

    @RequestMapping("/track/completePlay")
    public ResponseEntity<Boolean> completePlay(@Param("adid") String adid, @Param("bidid") String bidid, @Param("price") BigDecimal price) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");
        log.info("completePlay {} bid ", adid);
        return new ResponseEntity<>(true, headers, HttpStatus.OK);
    }

    @RequestMapping("/track/click")
    public ResponseEntity<Boolean> click(@Param("adid") String adid, @Param("bidid") String bidid, @Param("price") BigDecimal price) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");
        log.info("click {} bid ", adid);
        return new ResponseEntity<>(true, headers, HttpStatus.OK);
    }

    /**
     * 分页查询所有数据
     *
     * @param req 请求参数
     * @return 所有数据
     */
    @PostMapping("getAd")
    public ResponseEntity<BidResp> bid(@RequestBody @Validated BidRequest req) {
        Long id = SnowFlakeIdUtil.getInstance().nextId();
        log.info("bid request content: id:{},bidReq:{}", id, JSONUtil.toJsonStr(req));
//        BidReqLog bidReqLog = service.save(req.getId(), JSONUtil.toJsonStr(req));
        HttpHeaders headers = new HttpHeaders();
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");

        AdvChoiceStrategyEnum advChoiceStrategyEnum = AdvChoiceStrategyEnum.parse(strategy);
        IAdvertChoice advertChoice = advertChoiceFactory.getInstance(advChoiceStrategyEnum);
        if (advertChoice == null) {
            throw new BizException("Ad filtering policy does not support");
        }
        UserBO userBO = new UserBO();
        if (!StringUtils.isEmpty(req.getDevice().getOs())) {
            OsEnum osEnum = OsEnum.parse(req.getDevice().getOs());
            userBO.setOsType(osEnum.getValue());
        }
        if (req.getUser() != null) {
            GenderEnum genderEnum = GenderEnum.parse(req.getUser().getGender());
            userBO.setGender(genderEnum.getValue());
            Integer age = DateUtils.calAge(req.getUser().getYob());
            if (age != null) {
                userBO.setAge(age);
            }
        }
        if (req.getDevice().getGeo() != null) {
            userBO.setCountry(req.getDevice().getGeo().getCountry());
            userBO.setRegion(req.getDevice().getGeo().getRegion());
        }
        //挑选广告
        Advert advert = advertChoice.choose(waitChooseAdvertList, userBO);
        BidResp bidResp = new BidResp();
        bidResp.setId(req.getId());
        bidResp.setBidid(id.toString());
        bidResp.setCur(CUR);
        List<Seatbid> seatbidList = new ArrayList<>();
        Seatbid seatbid = new Seatbid();
        seatbidList.add(seatbid);
        seatbid.setSeat(SEAT_LIST.get(RandomUtil.randomInt(4)));
        List<Bid> bidList = new ArrayList<>();
        seatbid.setBid(bidList);
        Bid bid = new Bid();
        bid.setId(SnowFlakeIdUtil.getInstance().nextId().toString());
        bid.setImpid(req.getImp().get(0).getId());
        if (advert != null) {
            BigDecimal bidFloor = new BigDecimal(req.getImp().get(0).getBidfloor());
            if (bidFloor.compareTo(advert.getBidPrice()) > 0) {
                return new ResponseEntity<>(HttpStatus.NO_CONTENT);
            }
            bid.setAdid(advert.getId().toString());
            bid.setPrice(advert.getBidPrice());
            bid.setAdm(advert.getAdm());
            bid.setCid(advert.getCid());
            bid.setCrid(advert.getCrid());
            bid.setNurl(NURL.replace("{AD_ID}", advert.getId().toString()));
            bid.setBurl(BURL.replace("{AD_ID}", advert.getId().toString()));
            bid.setLurl(LURL.replace("{AD_ID}", advert.getId().toString()));
        } else {
            return new ResponseEntity<>(HttpStatus.NO_CONTENT);
        }
        bid.setAdomain(ADOMAIN);
        if (req.getDevice().getOs().equalsIgnoreCase("ios")) {
            bid.setBundle(BUNDLE_IOS_LIST.get(RandomUtil.randomInt(4)));
        } else {
            bid.setBundle(BUNDLE_ANDROID_LIST.get(RandomUtil.randomInt(4)));
        }
        bidList.add(bid);
        bidResp.setSeatbid(seatbidList);
        log.error("bidResp:{}", JSONUtil.toJsonStr(bidResp));
        return new ResponseEntity<>(bidResp, headers, HttpStatus.OK);
    }

}