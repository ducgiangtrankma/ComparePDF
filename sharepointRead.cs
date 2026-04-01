using System;
using System.Linq;
using System.Net;
using Action_DigitalSignatures_CyberHSM.Constants;

using System.Security;
using System.Collections.Generic;

namespace Action_DigitalSignatures_CyberHSM.Services
{
    using iTextSharp.text.pdf.qrcode;
    using iTextSharp.text.pdf;
    using iTextSharp.text;
    using Microsoft.Xrm.Sdk;
    using System;
    using System.Data.SqlTypes;
    using System.IO;
    using System.Text;
    using System.Xml;
    using System.Xml.Serialization;
    using ZXing;
    using System.Drawing;
    using ZXing.QrCode;
    using iTextSharp.text.pdf.parser;
    using Org.BouncyCastle.Asn1.Ocsp;
    using iTextSharp.text.pdf.codec;
    using System.Net.Http.Headers;
    using System.Net.Http;
    using System.Threading.Tasks;
    using System.Diagnostics;
    using Newtonsoft.Json.Linq;
    using Newtonsoft.Json;

    public class ResponseModel
    {
        public int statusCode { get; set; }
        public dynamic body { get; set; }
    }

    [XmlRoot("feed", Namespace = "http://www.w3.org/2005/Atom")]
    public class Feed
    {
        [XmlElement("id")]
        public string Id { get; set; }

        [XmlElement("title")]
        public string Title { get; set; }

        [XmlElement("updated")]
        public DateTime Updated { get; set; }

        [XmlElement("entry")]
        public List<Entry> Entry { get; set; }
    }

    public class Entry
    {
        [XmlElement("id")]
        public string Id { get; set; }

        [XmlElement("category")]
        public Category Category { get; set; }

        [XmlElement("link")]
        public List<Link> Links { get; set; }

        [XmlElement("title")]
        public string Title { get; set; }

        [XmlElement("updated")]
        public DateTime Updated { get; set; }

        [XmlElement("author")]
        public Author Author { get; set; }

        [XmlElement("content")]
        public Content Content { get; set; }
    }

    public class Category
    {
        [XmlAttribute("term")]
        public string Term { get; set; }

        [XmlAttribute("scheme")]
        public string Scheme { get; set; }
    }

    public class Link
    {
        [XmlAttribute("rel")]
        public string Rel { get; set; }

        [XmlAttribute("href")]
        public string Href { get; set; }
    }

    public class Author
    {
        [XmlElement("name")]
        public string Name { get; set; }
    }

    public class Content
    {
        [XmlElement("properties", Namespace = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata")]
        public Properties Properties { get; set; }
    }

    public class Properties
    {
        [XmlElement("CheckInComment", Namespace = "http://schemas.microsoft.com/ado/2007/08/dataservices")]
        public string CheckInComment { get; set; }
        [XmlElement("Name", Namespace = "http://schemas.microsoft.com/ado/2007/08/dataservices")]
        public string Name { get; set; }
        [XmlElement("ServerRelativeUrl", Namespace = "http://schemas.microsoft.com/ado/2007/08/dataservices")]
        public string ServerRelativeUrl { get; set; }

        // Add other properties here
    }
    public class SharePointService
    {
        private static SharePointService _instance;
        public static SharePointService Current
        {
            get { return _instance == null ? _instance = new SharePointService() : _instance; }
        }
        public SharePointService() { }
        static int GetPageCountFromBase64(string base64String)
        {
            byte[] bytes = Convert.FromBase64String(base64String);
            using (MemoryStream stream = new MemoryStream(bytes))
            {
                using (PdfReader reader = new PdfReader(stream))
                {
                    return reader.NumberOfPages;
                }
            }
        }
        static float GetPDFWidthFromBase64(string base64String)
        {
            byte[] bytes = Convert.FromBase64String(base64String);
            using (MemoryStream stream = new MemoryStream(bytes))
            {
                using (PdfReader reader = new PdfReader(stream))
                {
                    var page = reader.GetPageSize(1);
                    return page.Width;
                }
            }
        }
        public void Createfile(string base64String, string fileSigned, string documentLibraryName, string entityName = "", IOrganizationService service = null, ITracingService tracingService = null)
        {
            try
            {

                OrganizationRequest request = new OrganizationRequest();
                OrganizationResponse response = null;
                request = new OrganizationRequest("bsd_bsd_Action_Create_Folder_SharePoint");

                // lấy số điện thoại của khách để gửi
                string path = documentLibraryName.Replace("/" + fileSigned, "");
                request["Path_in"] = $"{path}";
                request["filename"] = fileSigned;
                request["base64String"] = base64String;
                response = service.Execute(request);
                // Convert base64 string to byte array
                //byte[] bytes = Convert.FromBase64String(base64String);

                //// Upload the PDF file to SharePoint
                //string siteUrl = UrlSSM.api;
                //ClientContext clientContext = new ClientContext(siteUrl);

                //// Provide your SharePoint Online credentials
                //clientContext.Credentials = credentials;
                //// Get the SharePoint web
                //Web web = clientContext.Web;
                ////clientContext.Load(web);
                //clientContext.ExecuteQuery();
                //// Get the folder by its server relative url
                //Folder folder = web.GetFolderByServerRelativeUrl(UrlSSM.api + "/" + documentLibraryName);
                //// Upload the file to the folder
                //FileCreationInformation newFile = new FileCreationInformation
                //{
                //    Content = bytes,
                //    Url = fileSigned,
                //    Overwrite = true
                //};
                //Microsoft.SharePoint.Client.File uploadFile = folder.Files.Add(newFile);
                //// Load the web and upload the file
                //clientContext.Load(uploadFile);
                //clientContext.ExecuteQuery();
            }
            catch (Exception ex)
            {
                if (tracingService != null)
                {
                    tracingService.Trace($"lỗi Createfile:{ex.Message}");
                }
                //for (int i = 0; i < 5; i++)
                //{
                //    try
                //    {
                //        OrganizationRequest request = new OrganizationRequest();
                //        OrganizationResponse response = null;
                //        request = new OrganizationRequest("bsd_Action_Create_Folder_SharePoint");
                //        // lấy số điện thoại của khách để gửi            
                //        request["Path_in"] = $"{documentLibraryName}";
                //        request["entityname_in"] = entityName;
                //        //response = service.Execute(request);
                //        // Convert base64 string to byte array
                //        byte[] bytes = Convert.FromBase64String(base64String);

                //        // Upload the PDF file to SharePoint
                //        string siteUrl = UrlSSM.api;
                //        ClientContext clientContext = new ClientContext(siteUrl);

                //        // Provide your SharePoint Online credentials
                //        clientContext.Credentials = credentials;
                //        // Get the SharePoint web
                //        Web web = clientContext.Web;
                //        //clientContext.Load(web);
                //        clientContext.ExecuteQuery();
                //        // Get the folder by its server relative url
                //        Folder folder = web.GetFolderByServerRelativeUrl(UrlSSM.api + "/"+documentLibraryName);
                //        // Upload the file to the folder
                //        FileCreationInformation newFile = new FileCreationInformation
                //        {
                //            Content = bytes,
                //            Url = fileSigned,
                //            Overwrite = true
                //        };
                //        Microsoft.SharePoint.Client.File uploadFile = folder.Files.Add(newFile);
                //        // Load the web and upload the file
                //        clientContext.Load(uploadFile);
                //        clientContext.ExecuteQuery();
                //        break;
                //    }
                //    catch (Exception ex2)
                //    {
                //        if(tracingService!= null)
                //        {
                //            tracingService.Trace($"lỗi Createfile:{ex.Message}");
                //        }
                //        throw ex2;
                //    }
                //}
                throw ex;

            }

        }
        public byte[] DownloadFileViaRestAPI2(string webUrl, ICredentials credentials, string documentLibName, string fileName)
        {
            try
            {



                webUrl = webUrl.EndsWith("/") ? webUrl.Substring(0, webUrl.Length - 1) : webUrl;
                string webRelativeUrl = null;
                if (webUrl.Split('/').Length > 3)
                {
                    webRelativeUrl = "/" + webUrl.Split(new char[] { '/' }, 4)[3];
                }
                else
                {
                    webRelativeUrl = "";
                }

                byte[] data = null;
                using (WebClient client = new WebClient())
                {
                    client.Headers.Add("X-FORMS_BASED_AUTH_ACCEPTED", "f");
                    client.Credentials = credentials;
                    Uri endpointUri = new Uri(webUrl + "/_api/web/GetFileByServerRelativeUrl('" + documentLibName + "/" + fileName + "')/$value");
                    data = client.DownloadData(endpointUri);
                }
                return data;
            }
            catch (Exception ex)
            {
                throw new Exception(ex.Message + " :" + webUrl + "/_api/web/GetFileByServerRelativeUrl('" + documentLibName + "/" + fileName + "')/$value");
            }

        }
        public byte[] DownloadFileViaRestAPI(string webUrl, string documentLibName, string fileName, ITracingService tracingService = null)
        {
            HttpClient client = new HttpClient();
            try
            {
                if (tracingService != null)
                    tracingService.Trace("start request:DownloadFileViaRestAPI");
                // Thiết lập HttpClient
                client.DefaultRequestHeaders.Accept.Clear();
                client.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

                // Thiết lập Basic Authentication
                var byteArray = Encoding.ASCII.GetBytes($"{UrlSSM.usernameSP}:{UrlSSM.passwordSP}");
                if (tracingService != null)

                    tracingService.Trace("start request:1");
                // Tạo nội dung yêu cầu JSON
                var location = documentLibName + "/" + fileName;
                location = location.Replace(UrlSSM.fileUrlSP, "").Replace("//", "");
                var jsonPayload = $"{{\"url\":\"{webUrl}\", \"location\":\"{location}\"}}";
                // Tạo nội dung yêu cầu
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                // Gửi yêu cầu POST đến Power Automate
                HttpResponseMessage response = client.PostAsync(UrlSSM.urlGetFileSharePoint, content).Result;
                if (tracingService != null)

                    tracingService.Trace("start request:2");
                // Kiểm tra phản hồi
                response.EnsureSuccessStatusCode();
                if (tracingService != null)

                    tracingService.Trace("status request:" + response.StatusCode.ToString());
                // Đọc nội dung phản hồi
                string responseBody = response.Content.ReadAsStringAsync().Result;

                // Lấy nội dung từ body
                if (tracingService != null)

                    tracingService.Trace("step 123213");
                if (response.StatusCode == HttpStatusCode.OK)
                {

                    string base64Content = responseBody;
                    if (tracingService != null)

                        tracingService.Trace("step 123213!");

                    // Chuyển đổi từ base64 thành byte[]
                    byte[] fileContent = Convert.FromBase64String(base64Content);
                    if (tracingService != null)

                        tracingService.Trace("step 123213##");

                    return fileContent;
                    // Bây giờ bạn có thể sử dụng fileContent (byte[]) theo nhu cầu
                    // Ví dụ: lưu vào file, gửi email, v.v.
                }
                else
                {
                    throw new Exception("không tìm thấy files: " + location);
                }
            }
            catch (Exception ex)
            {
                var location = documentLibName + "/" + fileName;
                location = location.Replace(UrlSSM.fileUrlSP, "").Replace("//", "");
                if (tracingService != null)

                    tracingService.Trace(" request:jsonPayload " + $"{{\"url\":\"{webUrl}\", \"location\":\"{location}\"}}");
                if (tracingService != null)

                    tracingService.Trace(" error " + ex.Message);
                throw new Exception(ex.Message + " \nrequest:jsonPayload" + $"{{\"url\":\"{webUrl}\", \"location\":\"{location}\"}}");
            }
        }
        #region download file by PA
        #region Delete File by PA
        public void DeleteFile(string filePath, ITracingService tracingService = null)
        {
            HttpClient client = new HttpClient();
            var webUrl = $"https://tngholding.sharepoint.com{UrlSSM.fileUrlSP}";
            
           

            try
            {
                if (tracingService != null)
                    tracingService.Trace("start request:");
                // Thiết lập HttpClient
                client.DefaultRequestHeaders.Accept.Clear();
                client.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

                // Thiết lập Basic Authentication
                var byteArray = Encoding.ASCII.GetBytes($"{UrlSSM.usernameSP}:{UrlSSM.passwordSP}");
                if (tracingService != null)

                    tracingService.Trace("start request:1");
                // Tạo nội dung yêu cầu JSON
                var location = filePath;
                location = location.Replace(UrlSSM.fileUrlSP, "").Replace("//", "");
                var jsonPayload = $"{{\"url\":\"{webUrl}\", \"location\":\"/{location}\"}}";
                // Tạo nội dung yêu cầu
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                // Gửi yêu cầu POST đến Power Automate
                HttpResponseMessage response = client.PostAsync(UrlSSM.urlDeleteFileSharePoint, content).Result;
                if (tracingService != null)

                    tracingService.Trace("start request:2");
                // Kiểm tra phản hồi
                response.EnsureSuccessStatusCode();
                if (tracingService != null)

                    tracingService.Trace("status request:" + response.StatusCode.ToString());
                if (tracingService != null)
                    tracingService.Trace("step Ok");
                if (response.StatusCode == HttpStatusCode.OK)
                {

                 
                }
                else
                {
                    throw new Exception("lỗi xóa file: " + location);
                }
            }
            catch (Exception ex)
            {
                var location = filePath;
                if (tracingService != null)

                    tracingService.Trace(" request:jsonPayload " + $"{{\"url\":\"{webUrl}\", \"location\":\"{location}\"}}");
                if (tracingService != null)

                    tracingService.Trace(" error " + ex.Message);
                throw new Exception(ex.Message + " \nrequest:jsonPayload" + $"{{\"url\":\"{webUrl}\", \"location\":\"{location}\"}}");
            }
        }
        #endregion
        public byte[] DownloadFileViaRestAPI3(string webUrl, ICredentials credentials, string documentLibName, string fileName)
        {
            try
            {



                webUrl = webUrl.EndsWith("/") ? webUrl.Substring(0, webUrl.Length - 1) : webUrl;
                string webRelativeUrl = null;
                if (webUrl.Split('/').Length > 3)
                {
                    webRelativeUrl = "/" + webUrl.Split(new char[] { '/' }, 4)[3];
                }
                else
                {
                    webRelativeUrl = "";
                }

                byte[] data = null;
                using (WebClient client = new WebClient())
                {
                    client.Headers.Add("X-FORMS_BASED_AUTH_ACCEPTED", "f");
                    client.Credentials = credentials;
                    Uri endpointUri = new Uri(webUrl + "/_api/web/GetFileByServerRelativeUrl('" + documentLibName + "/" + fileName + "')/$value");
                    data = client.DownloadData(endpointUri);
                }
                return data;
            }
            catch (Exception ex)
            {
                throw new Exception(ex.Message + " :" + webUrl + "/_api/web/GetFileByServerRelativeUrl('" + documentLibName + "/" + fileName + "')/$value");
            }

        }
        #endregion
        #region
        public List<string> GetAllFileName(string UrlFolder, ITracingService tracingService, string typefile = "", List<string> lstid = null)
        {
            HttpClient client = new HttpClient();
            var webUrl = $"https://tngholding.sharepoint.com{UrlSSM.fileUrlSP}";
            try
            {
                if (tracingService != null)
                    tracingService.Trace("start request:");
                // Thiết lập HttpClient
                client.DefaultRequestHeaders.Accept.Clear();
                client.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

                // Thiết lập Basic Authentication
                var byteArray = Encoding.ASCII.GetBytes($"{UrlSSM.usernameSP}:{UrlSSM.passwordSP}");
                if (tracingService != null)

                    tracingService.Trace("start request:1");
                // Tạo nội dung yêu cầu JSON
                var location = UrlFolder;
                location = location.Replace(UrlSSM.fileUrlSP, "").Replace("//", "");
                if (string.IsNullOrEmpty(typefile))
                    typefile = "all";
                var jsonPayload = $"{{\"url\":\"{webUrl}\", \"location\":\"/{location}\",\"typefile\":\"{typefile}\"}}";
                // Tạo nội dung yêu cầu
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                // Gửi yêu cầu POST đến Power Automate
                HttpResponseMessage response = client.PostAsync(UrlSSM.urlGetAllFilesNameSharePoint, content).Result;
                if (tracingService != null)

                    tracingService.Trace("start request:2");
                // Kiểm tra phản hồi
                response.EnsureSuccessStatusCode();
                if (tracingService != null)

                    tracingService.Trace("status request:" + response.StatusCode.ToString());
                tracingService.Trace("step Ok");
                if (response.StatusCode == HttpStatusCode.OK)
                {
                    string responseBody = response.Content.ReadAsStringAsync().Result;
                    if(string.IsNullOrEmpty(responseBody)) { return new List<string>(); }
                    var lstName=responseBody.Split(',').ToList();
                    tracingService.Trace(JsonConvert.SerializeObject(lstName));

                    if (lstid != null)
                    {
                        try
                        {
                            string siteUrlRoot = $"https://tngholding.sharepoint.com/{UrlSSM.fileUrlSP}";
                            using (var clientContext = new Microsoft.SharePoint.Client.ClientContext(siteUrlRoot))
                            {
                                System.Security.SecureString secureString = new System.Security.SecureString();
                                foreach (char c in UrlSSM.passwordSP.ToCharArray())
                                {
                                    secureString.AppendChar(c);
                                }
                                clientContext.Credentials = new Microsoft.SharePoint.Client.SharePointOnlineCredentials(UrlSSM.usernameSP, secureString);

                                foreach (var item in lstName)
                                {
                                    string encodedItem = Uri.EscapeDataString(item);
                                    
                                    var locationSubPath = UrlFolder.Replace(UrlSSM.fileUrlSP, "").Replace("//", "");
                                    if(locationSubPath.StartsWith("/")) locationSubPath = locationSubPath.Substring(1);

                                    string relativeUrl = $"/{UrlSSM.fileUrlSP}/{locationSubPath}/{encodedItem}".Replace("//", "/");
                                    Microsoft.SharePoint.Client.File file = clientContext.Web.GetFileByServerRelativeUrl(relativeUrl);
                                    clientContext.Load(file, f => f.ListItemAllFields);
                                    clientContext.ExecuteQuery();

                                    int itemId = file.ListItemAllFields.Id;
                                    tracingService.Trace($"ListItemAllFields ID for {item}: {itemId}");
                                    lstid.Add(itemId.ToString());
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            tracingService.Trace("Error getting List Item IDs: " + ex.Message);
                        }
                    }

                    return lstName;

                }
                else
                {
                    return new List<string>();
                }
            }
            catch (Exception ex)
            {
               
               return new List<string>();
            }
        }
        #endregion
        //public List<string> GetAllFileName2(string UrlFolder, ITracingService tracingService, string typefile = "", List<string> lstid = null)
        //{
        //    tracingService.Trace("url :" + UrlFolder);
        //    List<string> fileNames = new List<string>();
        //    string siteUrlRoot = $"https://tngholding.sharepoint.com/{UrlSSM.fileUrlSP}";
        //    // Đăng nhập vào SharePoint
        //    List<string> streeFolder = UrlFolder.Split('/').ToList();
        //    ClientContext clientContext = new ClientContext(siteUrlRoot);
        //    SecureString secureString = new SecureString();

        //    foreach (char c in "rox@2024".ToCharArray())
        //    {
        //        secureString.AppendChar(c);
        //    }
        //    // Provide your SharePoint Online credentials
        //    clientContext.Credentials = new SharePointOnlineCredentials("bsdsupport@roxliving.vn", secureString);
        //    using (WebClient client = new WebClient())
        //    {
        //        client.Headers.Add("X-FORMS_BASED_AUTH_ACCEPTED", "f");
        //        client.Credentials = new SharePointOnlineCredentials("bsdsupport@roxliving.vn", secureString);
        //        Uri endpointUri = new Uri($"https://tngholding.sharepoint.com/{UrlSSM.fileUrlSP}" + "/_api/web/GetFolderByServerRelativeUrl('" + $"/{UrlSSM.fileUrlSP}/" + UrlFolder + "')/Files");
        //        var data = client.DownloadData(endpointUri);
        //        var str = System.Text.Encoding.Default.GetString(data);
        //        tracingService.Trace("xml - " + str);
        //        XmlSerializer serializer = new XmlSerializer(typeof(Feed));
        //        using (StringReader reader = new StringReader(str))
        //        {
        //            Feed feed = (Feed)serializer.Deserialize(reader);
        //            foreach (var item in feed.Entry)
        //            {
        //                byte[] utf8Bytes = Encoding.Default.GetBytes(item.Content.Properties.Name);
        //                string decodedString = Encoding.UTF8.GetString(utf8Bytes);
        //                var decodedStrings = decodedString.Split('.').ToList();
        //                if (typefile != "")
        //                {
        //                    if (decodedStrings[decodedStrings.Count - 1] != "pdf")
        //                    {
        //                        continue;
        //                    }
        //                }
        //                fileNames.Add(decodedString);
        //            }
        //            // Sử dụng đối tượng feed ở đây
        //        }
        //    }

        //    if (lstid != null)
        //    {

        //        foreach (var item in fileNames)
        //        {
        //            tracingService.Trace("UrlFolder " + UrlFolder);
        //            tracingService.Trace("item " + item);
        //            string encodedItem = Uri.EscapeDataString(item);
        //            tracingService.Trace("item " + encodedItem);
        //            Microsoft.SharePoint.Client.File file = clientContext.Web.GetFileByUrl(UrlFolder + "/" + encodedItem);
        //            // Load ListItemAllFields để truy cập các thuộc tính của ListItem
        //            clientContext.Load(file, f => f.ListItemAllFields);
        //            // Thực thi query
        //            clientContext.ExecuteQuery();
        //            // Lấy ID của ListItem
        //            int itemId = file.ListItemAllFields.Id;
        //            tracingService.Trace("ListItemAllFields ID: " + itemId);
        //            lstid.Add(itemId.ToString());
        //        }
        //    }
        //    return fileNames;
        //}
        //public void DeleteFile2(string filePath, ITracingService tracingService = null)
        //{
        //    if (tracingService != null)
        //    {
        //        tracingService.Trace("delete path: " + filePath);
        //    }
        //    SecureString secureString = new SecureString();
        //    foreach (char c in "Tng@2024".ToCharArray())
        //    {
        //        secureString.AppendChar(c);
        //    }
        //    byte[] data = null;
        //    using (WebClient client = new WebClient())
        //    {
        //        client.Headers.Add("X-FORMS_BASED_AUTH_ACCEPTED", "f");
        //        string siteUrlRoot = $"https://tngholding.sharepoint.com/{UrlSSM.fileUrlSP}";
        //        client.Credentials = new SharePointOnlineCredentials("crmadmin@tngrealty.vn", secureString);
        //        Uri endpointUri = new Uri(siteUrlRoot + "/_api/web/GetFileByServerRelativeUrl('" + filePath + "')/$value");
        //        data = client.UploadData(siteUrlRoot + "/" + filePath, "DELETE", new byte[0]);
        //    }
        //}
        public string GenQRcode(string content, string base64String)
        {
            string encodedUrl = Uri.EscapeUriString(content);
            byte[] utf8Bytes = Encoding.Default.GetBytes(encodedUrl);
            string contents = Encoding.UTF8.GetString(utf8Bytes);
            // Tạo mã QR code từ nội dung cần nhúng
            BarcodeWriter barcodeWriter = new BarcodeWriter();
            var writer = new BarcodeWriter
            {
                Format = BarcodeFormat.QR_CODE,
                Options = new QrCodeEncodingOptions
                {
                    CharacterSet = "UTF-8",
                    Width = 70,
                    Height = 70
                }
            };

            var qrCodeBitmap = writer.Write(contents);
            int countPage = SharePointService.GetPageCountFromBase64(base64String);
            float width = (int)Math.Floor(SharePointService.GetPDFWidthFromBase64(base64String));
            string base64StringClone = "";
            // Lưu hình ảnh chứa mã QR code
            qrCodeBitmap.Save("qrcode.png");
            for (int i = 1; i <= countPage; i++)
            {

                base64StringClone = base64String;
                byte[] pdfBytes = Convert.FromBase64String(base64StringClone);

                // Đọc file PDF từ byte array
                using (MemoryStream pdfStream = new MemoryStream(pdfBytes))
                using (MemoryStream outputPdfStream = new MemoryStream())
                {

                    PdfReader pdfReader = new PdfReader(pdfStream);
                    using (PdfStamper pdfStamper = new PdfStamper(pdfReader, outputPdfStream))
                    {
                        // Lấy trang PDF cần gắn mã QR code
                        int pageNumber = i; // Ví dụ: gắn vào trang đầu tiên
                        PdfContentByte pdfContentByte = pdfStamper.GetOverContent(pageNumber);
                        // Chuyển đổi Bitmap QR code thành iTextSharp Image
                        iTextSharp.text.Image qrCodeImage = iTextSharp.text.Image.GetInstance(qrCodeBitmap, BaseColor.WHITE);
                        qrCodeImage.SetAbsolutePosition(500, 0); // Tọa độ x, y để gắn mã QR code
                        pdfContentByte.AddImage(qrCodeImage);
                    }
                    byte[] outputPdfBytes = outputPdfStream.ToArray();
                    base64String = Convert.ToBase64String(outputPdfBytes);
                }
                // Lưu file PDF mới chứa mã QR code dưới dạng chuỗi base64
            }
            return base64String;
        }
        public string RemoveSpecialCharacters(string input)
        {
            char[] charsToRemove = { '~', '"', '#', '%', '&', '*', ':', '<', '>', '?', '\\', '{', '|', '}' };
            return new string(input.Where(c => !charsToRemove.Contains(c)).ToArray());
        }
    }


}

