package com.leeyom.scaffold.help;

import com.aliyun.oss.ClientConfiguration;
import com.aliyun.oss.OSSClient;
import com.aliyun.oss.common.auth.DefaultCredentialProvider;
import com.aliyun.oss.model.PutObjectRequest;
import com.aliyun.oss.model.PutObjectResult;
import com.leeyom.scaffold.dto.req.BidRequest;
import com.leeyom.scaffold.utils.JsonUtils;
import lombok.extern.slf4j.Slf4j;

import java.io.InputStream;

/**
 * @Description: 阿里云 oss 上传工具类(高依赖版)
 * @Date: 2019/5/10
 */
@Slf4j
public class OssBootHelper {

    private static String endPoint;
    private static String accessKeyId;
    private static String accessKeySecret;
    private static String bucketName;
    private static String staticDomain;

    public static void setEndPoint(String endPoint) {
        OssBootHelper.endPoint = endPoint;
    }

    public static void setAccessKeyId(String accessKeyId) {
        OssBootHelper.accessKeyId = accessKeyId;
    }

    public static void setAccessKeySecret(String accessKeySecret) {
        OssBootHelper.accessKeySecret = accessKeySecret;
    }

    public static void setBucketName(String bucketName) {
        OssBootHelper.bucketName = bucketName;
    }

    public static void setStaticDomain(String staticDomain) {
        OssBootHelper.staticDomain = staticDomain;
    }

    public static String getStaticDomain() {
        return staticDomain;
    }

    public static String getEndPoint() {
        return endPoint;
    }

    public static String getAccessKeyId() {
        return accessKeyId;
    }

    public static String getAccessKeySecret() {
        return accessKeySecret;
    }

    public static String getBucketName() {
        return bucketName;
    }

    public static OSSClient getOssClient() {
        return ossClient;
    }

    /**
     * oss 工具客户端
     */
    private static OSSClient ossClient = null;


    /**
     * 初始化 oss 客户端
     *
     * @return
     */
    public static OSSClient initOSS(String endpoint, String accessKeyId, String accessKeySecret) {
        if (ossClient == null) {
            ossClient = new OSSClient(endpoint,
                    new DefaultCredentialProvider(accessKeyId, accessKeySecret),
                    new ClientConfiguration());
        }
        return ossClient;
    }


    /**
     * 上传文件到oss
     *
     * @param stream
     * @param relativePath
     * @return
     */
    public static Boolean upload(InputStream stream, String relativePath, String fileName) {
        String fileUrl = relativePath + fileName;
        initOSS(endPoint, accessKeyId, accessKeySecret);
        PutObjectRequest putRequest = new PutObjectRequest(bucketName, fileUrl, stream);
        putRequest.setTrafficLimit(30 * 1024 * 1024 * 8);  // 限制为30MB/s
        PutObjectResult result = ossClient.putObject(putRequest);
        if (result != null) {
            log.info("------OSS文件上传成功------" + fileUrl);
        } else {
            log.error("oss文件上传失败");
            return false;
        }
        return true;
    }

    public static void main(String[] args) {
        String line = "2025-08-28 05:41:30.323  INFO 13 --- [http-nio-9380-exec-115] c.leeyom.scaffold.api.BidProdController  : bid request content: id:1145714781761540096,bidReq:{\"app\":{\"ver\":\"1.0.0\",\"storeurl\":\"https://play.google.com/store/apps/details?id=com.kwai.video&shortlink=web&c=web&pid=web\",\"name\":\"Kwai\",\"publisher\":{},\"id\":\"1659174177910\",\"bundle\":\"com.kwai.video\"},\"tmax\":500,\"regs\":{\"ext\":{\"gdpr\":0}},\"imp\":[{\"ext\":{\"deeplink\":1},\"tagid\":\"video_br_1\",\"bidfloorcur\":\"USD\",\"video\":{\"ext\":{},\"linearity\":1,\"companiontype\":[1,2],\"h\":480,\"skip\":0,\"minduration\":10,\"mimes\":[\"video/mp4\"],\"maxduration\":1000,\"w\":320,\"api\":[1,2,3,4,5,6],\"protocols\":[2,3,7]},\"secure\":1,\"bidfloor\":0,\"id\":\"4851846452809353681\",\"instl\":1}],\"at\":1,\"id\":\"4851846452809353681\",\"device\":{\"os\":\"Android\",\"ifa\":\"5865d880-e91b-4c90-ba7c-db60babecf20\",\"ip\":\"177.221.107.194\",\"h\":1280,\"language\":\"pt\",\"dnt\":0,\"ua\":\"Dalvik/2.1.0 (Linux; U; Android 14; SM-A346M Build/UP1A.231005.007)\",\"devicetype\":4,\"geo\":{\"country\":\"BRA\"},\"lmt\":0,\"osv\":\"14\",\"w\":720,\"model\":\"SM-A346M\",\"connectiontype\":2,\"make\":\"samsung\"},\"user\":{\"id\":\"572671177\"}}\n";
        String jsonStr = line.split(",bidReq:")[1];
        String dateStr = line.substring(0, 19);
        BidRequest bidRequest = JsonUtils.Json2Object(jsonStr, BidRequest.class);
        System.out.println(dateStr);
        System.out.println(bidRequest.getUser().getId());
    }
}