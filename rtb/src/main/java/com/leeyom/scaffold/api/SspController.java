package com.leeyom.scaffold.api;


import cn.hutool.core.util.RandomUtil;
import com.leeyom.scaffold.dto.req.BidRequest;
import com.leeyom.scaffold.dto.resp.BidResp;
import com.leeyom.scaffold.enums.GenderEnum;
import com.leeyom.scaffold.enums.OsEnum;
import com.leeyom.scaffold.service.SspService;
import com.leeyom.scaffold.utils.JsonUtils;
import com.leeyom.scaffold.utils.SnowFlakeIdUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.util.Arrays;
import java.util.List;

/**
 * ssp请求
 *
 * @author luoxun
 * @since 2025-07-15 16:17:37
 */
@RestController
@RequestMapping("ssp")
@Slf4j
public class SspController {

    @Resource
    private SspService sspService;

    private static final String REQ_SAMPLE = "{\n" +
            "    \"id\": \"6675a52b8b6dcc1ad5c0389d\",\n" +
            "    \"imp\": [\n" +
            "        {\n" +
            "            \"id\": \"1\",\n" +
            "            \"banner\": {\n" +
            "                \"format\": [\n" +
            "                    {\n" +
            "                        \"w\": 320,\n" +
            "                        \"h\": 480\n" +
            "                    }\n" +
            "                ],\n" +
            "                \"w\": 320,\n" +
            "                \"h\": 480,\n" +
            "                \"pos\": 7,\n" +
            "                \"mimes\": [\n" +
            "                    \"image/jpg\",\n" +
            "                    \"image/gif\",\n" +
            "                    \"text/html\"\n" +
            "                ],\n" +
            "                \"api\": [\n" +
            "                    5,\n" +
            "                    7\n" +
            "                ],\n" +
            "                \"id\": \"1\",\n" +
            "                \"vcm\": 1\n" +
            "            },\n" +
            "            \"video\": {\n" +
            "                \"mimes\": [\n" +
            "                    \"video/mp4\"\n" +
            "                ],\n" +
            "                \"minduration\": 0,\n" +
            "                \"maxduration\": 120,\n" +
            "                \"protocols\": [\n" +
            "                    2,\n" +
            "                    5,\n" +
            "                    3,\n" +
            "                    6\n" +
            "                ],\n" +
            "                \"w\": 320,\n" +
            "                \"h\": 480,\n" +
            "                \"placement\": 5,\n" +
            "                \"plcmt\": 3,\n" +
            "                \"linearity\": 1,\n" +
            "                \"skip\": 1,\n" +
            "                \"skipafter\": 5,\n" +
            "                \"minbitrate\": 250,\n" +
            "                \"maxbitrate\": 15000,\n" +
            "                \"boxingallowed\": 1,\n" +
            "                \"playbackmethod\": [\n" +
            "                    1,\n" +
            "                    2,\n" +
            "                    3,\n" +
            "                    4\n" +
            "                ],\n" +
            "                \"delivery\": [\n" +
            "                    2,\n" +
            "                    1\n" +
            "                ],\n" +
            "                \"pos\": 7,\n" +
            "                \"companionad\": [\n" +
            "                    {\n" +
            "                        \"format\": [\n" +
            "                            {\n" +
            "                                \"w\": 320,\n" +
            "                                \"h\": 480\n" +
            "                            }\n" +
            "                        ],\n" +
            "                        \"w\": 320,\n" +
            "                        \"h\": 480,\n" +
            "                        \"pos\": 7,\n" +
            "                        \"api\": [\n" +
            "                            5\n" +
            "                        ],\n" +
            "                        \"id\": \"6675ae4e428c91f151e6011e-1\",\n" +
            "                        \"vcm\": 1\n" +
            "                    }\n" +
            "                ],\n" +
            "                \"api\": [\n" +
            "                    7\n" +
            "                ],\n" +
            "                \"companiontype\": [\n" +
            "                    1,\n" +
            "                    2\n" +
            "                ],\n" +
            "                \"ext\": {}\n" +
            "            },\n" +
            "            \"displaymanager\": \"JzTech\",\n" +
            "            \"displaymanagerver\": \"6.12.1\",\n" +
            "            \"instl\": 1,\n" +
            "            \"tagid\": \"PUBLISHER_PLACEMENT_ID\",\n" +
            "            \"bidfloor\": 4,\n" +
            "            \"bidfloorcur\": \"USD\",\n" +
            "            \"secure\": 1,\n" +
            "            \"ext\": {\n" +
            "                \"skadn\": {\n" +
            "                    \"version\": \"2.0\",\n" +
            "                    \"versions\": [\n" +
            "                        \"2.0\"\n" +
            "                    ],\n" +
            "                    \"sourceapp\": \"123456789\",\n" +
            "                    \"skadnetids\": [],\n" +
            "                    \"ext\": {\n" +
            "                        \"sko\": 1\n" +
            "                    }\n" +
            "                },\n" +
            "                \"deeplink\": 1,\n" +
            "                \"skpv\": 0,\n" +
            "                \"vxec\": 0,\n" +
            "                \"pcta\": 1\n" +
            "            }\n" +
            "        }\n" +
            "    ],\n" +
            "    \"app\": {\n" +
            "        \"id\": \"62d8fb315da899193f643165\",\n" +
            "        \"name\": \"JzTech Test App\",\n" +
            "        \"bundle\": \"123456789\",\n" +
            "        \"storeurl\": \"https://apps.apple.com/us/app/app_store_url\",\n" +
            "        \"cat\": [\n" +
            "            \"IAB1\",\n" +
            "            \"IAB9\"\n" +
            "        ],\n" +
            "        \"ver\": \"1\",\n" +
            "        \"privacypolicy\": 1,\n" +
            "        \"publisher\": {\n" +
            "            \"id\": \"56e0de2215a62b831800002b\",\n" +
            "            \"cat\": [\n" +
            "                \"IAB1\",\n" +
            "                \"IAB9\"\n" +
            "            ]\n" +
            "        },\n" +
            "        \"keywords\": \"managed\",\n" +
            "        \"ext\": {}\n" +
            "    },\n" +
            "    \"device\": {\n" +
            "        \"ua\": \"Mozilla/5.0 (iPhone; CPU iPhone OS 13_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148\",\n" +
            "        \"geo\": {\n" +
            "            \"lat\": 28.0109,\n" +
            "            \"lon\": -82.4948,\n" +
            "            \"type\": 2,\n" +
            "            \"ipservice\": 3,\n" +
            "            \"country\": \"USA\",\n" +
            "            \"region\": \"FL\",\n" +
            "            \"city\": \"Tampa\",\n" +
            "            \"zip\": \"33614\"\n" +
            "        },\n" +
            "        \"dnt\": 0,\n" +
            "        \"lmt\": 0,\n" +
            "        \"ip\": \"199.193.115.73\",\n" +
            "        \"devicetype\": 4,\n" +
            "        \"make\": \"Apple\",\n" +
            "        \"model\": \"iPhone\",\n" +
            "        \"os\": \"iOS\",\n" +
            "        \"osv\": \"13.4\",\n" +
            "        \"h\": 2688,\n" +
            "        \"w\": 1242,\n" +
            "        \"language\": \"en\",\n" +
            "        \"connectiontype\": 2,\n" +
            "        \"ifa\": \"00000000-0000-0000-0000-000000000000\",\n" +
            "        \"dpidsha1\": \"b602d594afd2b0b327e07a06f36ca6a7e42546d0\",\n" +
            "        \"ext\": {\n" +
            "            \"idfv\": \"25336879-2A81-4E49-818D-CAE28C2A97BB\",\n" +
            "            \"ifv\": \"25336879-2A81-4E49-818D-CAE28C2A97BB\",\n" +
            "            \"atts\": 0\n" +
            "        }\n" +
            "    },\n" +
            "    \"user\": {\n" +
            "        \"yob\": \"1990\",\n" +
            "        \"gender\": \"M\",\n" +
            "        \"buyeruid\":\"userID0001\"\n" +
            "    },\n" +
            "    \"at\": 1,\n" +
            "    \"tmax\": 1000,\n" +
            "    \"cur\": [\n" +
            "        \"USD\"\n" +
            "    ],\n" +
            "    \"bcat\": [\n" +
            "        \"IAB26\"\n" +
            "    ],\n" +
            "    \"badv\": [],\n" +
            "    \"bapp\": [],\n" +
            "    \"source\": {\n" +
            "        \"ext\": {\n" +
            "            \"schain\": {\n" +
            "                \"complete\": 1,\n" +
            "                \"nodes\": [\n" +
            "                    {\n" +
            "                        \"asi\": \"JzTech.com\",\n" +
            "                        \"sid\": \"56e0de2215a62b831800002b\",\n" +
            "                        \"rid\": \"6675a52b8b6dcc1ad5c0389d\",\n" +
            "                        \"hp\": 1\n" +
            "                    }\n" +
            "                ],\n" +
            "                \"ver\": \"1.0\"\n" +
            "            },\n" +
            "            \"omidpn\": \"JzTech\",\n" +
            "            \"omidpv\": \"6.12.1\"\n" +
            "        }\n" +
            "    },\n" +
            "    \"regs\": {\n" +
            "        \"ext\": {\n" +
            "            \"gdpr\": 0,\n" +
            "            \"us_privacy\": \"1---\"\n" +
            "        }\n" +
            "    },\n" +
            "    \"ext\": {}\n" +
            "}";
    // iOS 、Android 、Windows
    private final static List<Integer> OS_TYPE_RATIO = Arrays.asList(45, 45, 10);
    private final static Integer YOB_START = 1980;
    private final static Integer YOB_INTERVAL_MAX = 27;
    // M 、 F 、O
    private final static List<Integer> GENDER_TYPE_RATIO = Arrays.asList(40, 55, 5);


    private final static String APP_ID = "800839";
    private final static String APP_NAME = "Block Blast!";
    private final static String APP_BUNDLE = "com.block.juggle";
    private final static String APP_STORE_URL = "https://play.google.com/store/apps/details?id=com.block.juggle&hl=pt-br&gl=br";


    @PostMapping("req")
    public ResponseEntity<BidResp> req() {
        BidRequest bidRequest = JsonUtils.Json2Object(REQ_SAMPLE, BidRequest.class);
        bidRequest.setId(SnowFlakeIdUtil.getInstance().nextId().toString());
        bidRequest.getUser().setBuyeruid(SnowFlakeIdUtil.getInstance().nextId().toString());
        bidRequest.getUser().setYob(randomYob());
        bidRequest.getUser().setGender(randomGender());
        bidRequest.getDevice().setOs(randomOs());
        HttpHeaders headers = new HttpHeaders();
        bidRequest.getApp().setId(APP_ID);
        bidRequest.getApp().setName(APP_NAME);
        bidRequest.getApp().setBundle(APP_BUNDLE);
        bidRequest.getApp().setStoreurl(APP_STORE_URL);
        headers.add("Content-Type", "application/json");
        headers.add("X-OpenRTB-Version", "2.5");
        BidResp bidResp = sspService.req(bidRequest);
        log.info("广告信息：{}", JsonUtils.Object2Json(bidResp));
        return new ResponseEntity<>(bidResp, headers, HttpStatus.OK);
    }

    private String randomYob() {
        Integer interval = RandomUtil.randomInt(0, YOB_INTERVAL_MAX);
        return String.valueOf(YOB_START + interval);
    }

    private String randomGender() {
        Integer interval = RandomUtil.randomInt(0, 100);
        if (interval < GENDER_TYPE_RATIO.get(0)) {
            return GenderEnum.MALE.getValue();
        }
        if (interval < GENDER_TYPE_RATIO.get(0) + GENDER_TYPE_RATIO.get(1)) {
            return GenderEnum.FEMALE.getValue();
        }
        return GenderEnum.KNOWN.getValue();
    }

    private String randomOs() {
        Integer interval = RandomUtil.randomInt(0, 100);
        if (interval < OS_TYPE_RATIO.get(0)) {
            return OsEnum.iOS.getValue();
        }
        if (interval < OS_TYPE_RATIO.get(0) + OS_TYPE_RATIO.get(1)) {
            return OsEnum.ANDROID.getValue();
        }
        return OsEnum.UNKNOWN.getValue();
    }
}